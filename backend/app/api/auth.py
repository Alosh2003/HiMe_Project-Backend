from datetime import datetime, timedelta, timezone
import hashlib
import os
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks
import httpx
from pydantic import BaseModel, EmailStr
from sqlalchemy.orm import Session
from google.oauth2 import id_token
from google.auth.transport import requests as google_requests
from jose import jwt, JWTError
from app.repositories.company_repo import CompanyRepository
from app.db.session import get_db
from app.schemas.user import (
    ApiResponseLogin,
    RegisterRequest,
    ApiResponseUser,
    UserObject,
    LoginRequest,
    VerifyEmailRequest,
    GoogleLoginRequest,
    VerifyResetCodeRequest,
    SetNewPasswordRequest,
    ForgotPasswordRequest,
)
from app.schemas.response import ErrorResponse
from app.core.security import generate_otp, hash_password, verify_password
from app.repositories.user_repo import UserRepository
from app.repositories.seeker_repo import SeekerRepository
from app.core.jwt import create_access_token
from app.models.user import (
    OAuthProvider,
    User,
    OAuthAccount,
    UserRole,
    VerificationCode,
    TokenType,
)
from app.core.email import send_verification_email
from app.core.rate_limit import rate_limit_ip
from app.schemas.user import FacebookLoginRequest
from app.schemas.user import LinkedInLoginRequest
SECRET_KEY = os.getenv("SECRET_KEY", "your-fallback-secret-key-for-development")
ALGORITHM = os.getenv("ALGORITHM", "HS256")
GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID")
FACEBOOK_APP_ID = os.getenv("FACEBOOK_APP_ID")
FACEBOOK_APP_SECRET = os.getenv("FACEBOOK_APP_SECRET")

router = APIRouter(prefix="/auth", tags=["Auth"])
ip_limit_otp = rate_limit_ip(max_requests=5, window_minutes=60, action="otp_request")

# ==========================================
# دالة فحص وإصدار الأكواد المركزية (Rate Limiting & OTP Generator)
# ==========================================
def issue_otp_code(user: User, token_type: TokenType, db: Session) -> str:
    now = datetime.now(timezone.utc)

    # 1. التحقق من الحظر المؤقت
    if user.blocked_until and user.blocked_until > now:
        remaining_hours = int((user.blocked_until - now).total_seconds() // 3600)
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"Too many requests. Your account is temporarily blocked for {remaining_hours} more hours.",
        )

    # 2. فحص الأكواد الصادرة مؤخراً (خلال آخر 24 ساعة مثلاً)
    recent_codes = (
        db.query(VerificationCode)
        .filter(
            VerificationCode.user_id == user.id,
            VerificationCode.token_type == token_type,
            VerificationCode.created_at >= now - timedelta(days=1),
        )
        .order_by(VerificationCode.created_at.desc())
        .all()
    )

    # 3. التحقق من تجاوز الحد الأقصى (مثلاً كودين) -> تفعيل الحظر لـ 3 أيام
    if len(recent_codes) >= 2:
        user.blocked_until = now + timedelta(days=3)
        db.commit()
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Maximum verification attempts reached. Your account has been temporarily restricted for 3 days.",
        )

    # 4. منع التكرار اللحظي: منع طلب كود جديد إذا كان الكود السابق لم ينتهِ بعد
    latest_code = recent_codes[0] if recent_codes else None
    if latest_code and not latest_code.is_used and latest_code.expires_at > now:
        remaining_seconds = int((latest_code.expires_at - now).total_seconds())
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"An active code already exists. Please check your email or wait {remaining_seconds} seconds before requesting a new one.",
        )

    # 5. إبطال جميع الأكواد السابقة النشطة
    db.query(VerificationCode).filter(
        VerificationCode.user_id == user.id,
        VerificationCode.token_type == token_type,
        VerificationCode.is_used == False,
    ).update({"is_used": True})

    # 6. إنشاء الكود الجديد مع صلاحية 20 دقيقة
    plain_code, code_hash = generate_otp(6)
    expires_at = now + timedelta(minutes=20)

    db_code = VerificationCode(
        user_id=user.id,
        code_hash=code_hash,
        token_type=token_type,
        target=user.email,
        expires_at=expires_at,
    )
    db.add(db_code)
    db.commit()

    return plain_code


# ==========================================
# مسارات التوثيق
# ==========================================
@router.post(
    "/login",
    response_model=ApiResponseLogin,
    status_code=status.HTTP_200_OK,
    responses={401: {"model": ErrorResponse}},
)
def login(request: LoginRequest, db: Session = Depends(get_db)):
    user_repo = UserRepository(db)

    # 1. البحث عن المستخدم عبر الإيميل[cite: 1, 4]
    user = user_repo.get_by_email(request.email)

    # 2. التحقق من وجود المستخدم وصحة كلمة المرور[cite: 1, 4]
    if not user or not verify_password(request.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials",
        )

    # 3. توليد الـ JWT Access Token[cite: 1, 4]
    access_token = create_access_token(
        data={"sub": str(user.id), "role": user.role}
    )

    # 4. إرجاع كود 200 OK بالشكل المعتمد في الوثيقة[cite: 4]
    return ApiResponseLogin(
        success=True,
        message="Login successful",
        data={
            "access_token": access_token,
            "token_type": "Bearer",
            "user": {
                "id": str(user.id),
                "email": user.email,
                "role": user.role,
            },
        },
    )

@router.post(
    "/register",
    response_model=ApiResponseUser,
    status_code=status.HTTP_201_CREATED,
    responses={409: {"model": ErrorResponse}},
)
def register(
    request: RegisterRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    _rate_limit: None = Depends(ip_limit_otp),
):
    user_repo = UserRepository(db)
    seeker_repo = SeekerRepository(db)
    company_repo = CompanyRepository(db)

    # تحديد نوع الحساب المختار (الافتراضي باحث عن عمل إن لم يُمرر)
    selected_role = getattr(request, "role", UserRole.JOB_SEEKER)

    # 1. التحقق من البريد وحالة التوثيق
    existing_user = user_repo.get_by_email(request.email)
    if existing_user:
        if existing_user.is_verified:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Email is already registered and verified.",
            )

        plain_code = issue_otp_code(existing_user, TokenType.EMAIL_VERIFY, db)
        print(f"--> [OTP Code for {existing_user.email}]: {plain_code}")
        background_tasks.add_task(send_verification_email, existing_user.email, plain_code)

        return ApiResponseUser(
            success=True,
            message="Account already exists but is not verified. A new verification code has been sent.",
            data=UserObject(
                id=existing_user.id,
                email=existing_user.email,
                role=existing_user.role,
            ),
        )

    # 2. تشفير كلمة المرور وإنشاء المستخدم بالنوع المختار
    hashed_pwd = hash_password(request.password)
    new_user = user_repo.create_user(
        email=request.email,
        password_hash=hashed_pwd,
        role=request.role,
    )

    # 3. إنشاء البروفايل المناسب لنوع الحساب
    if new_user.role == UserRole.COMPANY or str(new_user.role) == "company":
        company_repo.create_company_profile(user_id=new_user.id)
    else:
        seeker_repo.create_profile(user_id=new_user.id)

    # 4. توليد وحفظ كود التحقق
    plain_code = issue_otp_code(new_user, TokenType.EMAIL_VERIFY, db)
    print(f"--> [OTP Code for {new_user.email}]: {plain_code}")
    background_tasks.add_task(send_verification_email, new_user.email, plain_code)

    # 5. إرجاع الرد
    user_data = UserObject(
        id=new_user.id,
        email=new_user.email,
        role=new_user.role,
    )
    return ApiResponseUser(
        success=True,
        message="Account created successfully. Please verify your email.",
        data=user_data,
    )

@router.post(
    "/verify-email",
    status_code=status.HTTP_200_OK,
    responses={
        400: {"model": ErrorResponse},
        404: {"model": ErrorResponse},
    },
)
def verify_email(request: VerifyEmailRequest, db: Session = Depends(get_db)):
    user_repo = UserRepository(db)

    # 1. التأكد من وجود المستخدم[cite: 4]
    user = user_repo.get_by_email(request.email)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )

    # 2. إذا كان الحساب موثقاً مسبقاً[cite: 4]
    if user.is_verified:
        return {
            "success": True,
            "message": "Email is already verified",
        }

    # 3. تشفير الرمز المدخل لمقارنته[cite: 4]
    input_hash = hashlib.sha256(request.code.encode("utf-8")).hexdigest()

    # 4. البحث عن أحدث كود صالح لهذا المستخدم والنوع[cite: 4]
    now = datetime.now(timezone.utc)
    db_code = (
        db.query(VerificationCode)
        .filter(
            VerificationCode.user_id == user.id,
            VerificationCode.token_type == TokenType.EMAIL_VERIFY,
            VerificationCode.is_used == False,
            VerificationCode.expires_at > now,
        )
        .order_by(VerificationCode.created_at.desc())
        .first()
    )

    # 5. إذا لم نجد كوداً صالحاً (منتهي الصلاحية أو غير موجود)[cite: 4]
    if not db_code:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Verification code has expired or is invalid. Please request a new one.",
        )

    # 6. مطابقة الرمز وقفل الكود عند تجاوز 3 محاولات
    if db_code.code_hash != input_hash:
        db_code.attempts += 1
        if db_code.attempts >= 3:
            db_code.is_used = True  # إبطال الكود لمنع تخمينه
            db.commit()
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Too many incorrect attempts. This code has been invalidated. Please request a new one.",
            )
        db.commit()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Incorrect code. {3 - db_code.attempts} attempts remaining.",
        )

    # 7. نجاح التحقق: تحديث حالة المستخدم والكود[cite: 4]
    db_code.is_used = True
    user.is_verified = True
    db.commit()

    return {
        "success": True,
        "message": "Email verified successfully",
    }


class ResendCodeRequest(BaseModel):
    email: EmailStr


@router.post("/resend-code", status_code=status.HTTP_200_OK)
def resend_verification_code(
    request: ResendCodeRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    _rate_limit: None = Depends(ip_limit_otp),
):
    user_repo = UserRepository(db)
    user = user_repo.get_by_email(request.email)

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )

    if user.is_verified:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Account is already verified. Please login directly.",
        )

    # توليد وحفظ كود التحقق باستخدام issue_otp_code
    plain_code = issue_otp_code(user, TokenType.EMAIL_VERIFY, db)

    # إرسال الكود الجديد عبر البريد
    background_tasks.add_task(send_verification_email, user.email, plain_code)

    return {
        "success": True,
        "message": "A new verification code has been sent to your email.",
    }


@router.post("/forgot-password", status_code=status.HTTP_200_OK)
def forgot_password(
    request: ForgotPasswordRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    _rate_limit: None = Depends(ip_limit_otp),
):
    user_repo = UserRepository(db)
    user = user_repo.get_by_email(request.email)

    # حماية أمنية: إرجاع نجاح حتى لو لم يكن البريد موجوداً لمنع تخمين الإيميلات[cite: 4]
    if not user:
        return {
            "success": True,
            "message": "If this email is registered, a password reset code has been sent.",
        }

    # توليد وحفظ كود الاستعادة باستخدام issue_otp_code
    plain_code = issue_otp_code(user, TokenType.PASSWORD_RESET, db)

    # إرسال الكود في الخلفية[cite: 4]
    print(f"--> [Password Reset OTP for {user.email}]: {plain_code}")
    background_tasks.add_task(send_verification_email, user.email, plain_code)

    return {
        "success": True,
        "message": "If this email is registered, a password reset code has been sent.",
    }


@router.post("/verify-reset-code", status_code=status.HTTP_200_OK)
def verify_reset_code(request: VerifyResetCodeRequest, db: Session = Depends(get_db)):
    user_repo = UserRepository(db)
    user = user_repo.get_by_email(request.email)

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )

    input_hash = hashlib.sha256(request.code.encode("utf-8")).hexdigest()
    now = datetime.now(timezone.utc)

    db_code = (
        db.query(VerificationCode)
        .filter(
            VerificationCode.user_id == user.id,
            VerificationCode.token_type == TokenType.PASSWORD_RESET,
            VerificationCode.is_used == False,
            VerificationCode.expires_at > now,
        )
        .order_by(VerificationCode.created_at.desc())
        .first()
    )

    if not db_code:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired reset code",
        )

    # التحقق من المطابقة وقفل الكود عند تجاوز 3 محاولات
    if db_code.code_hash != input_hash:
        db_code.attempts += 1
        if db_code.attempts >= 3:
            db_code.is_used = True  # إبطال الكود لمنع تخمينه
            db.commit()
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Too many incorrect attempts. This code has been invalidated. Please request a new one.",
            )
        db.commit()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Incorrect code. {3 - db_code.attempts} attempts remaining.",
        )

    db_code.is_used = True
    db.commit()

    reset_payload = {
        "sub": str(user.id),
        "purpose": "password_reset",
        "exp": datetime.now(timezone.utc) + timedelta(minutes=20),
    }
    reset_token = jwt.encode(reset_payload, SECRET_KEY, algorithm=ALGORITHM)

    return {
        "success": True,
        "message": "Code verified successfully",
        "reset_token": reset_token,
    }


@router.post("/reset-password", status_code=status.HTTP_200_OK)
def set_new_password(request: SetNewPasswordRequest, db: Session = Depends(get_db)):
    try:
        payload = jwt.decode(request.reset_token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id = payload.get("sub")
        purpose = payload.get("purpose")

        if not user_id or purpose != "password_reset":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid token purpose",
            )
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Reset session has expired. Please request a new code.",
        )

    user_repo = UserRepository(db)
    user = user_repo.get_by_id(UUID(user_id))

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )

    new_hashed_pwd = hash_password(request.new_password)
    user_repo.update_password(user.id, new_hashed_pwd)

    return {
        "success": True,
        "message": "Password has been reset successfully. You can now login.",
    }


@router.post("/google", status_code=status.HTTP_200_OK)
def google_auth(request: GoogleLoginRequest, db: Session = Depends(get_db)):
    # 1. التحقق من التوكن من Google[cite: 4]
    try:
        id_info = id_token.verify_oauth2_token(
            request.id_token,
            google_requests.Request(),
            GOOGLE_CLIENT_ID,
        )
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired Google token",
        )

    google_account_id = id_info.get("sub")
    email = id_info.get("email")

    user_repo = UserRepository(db)
    seeker_repo = SeekerRepository(db)

    # 2. البحث في جدول oauth_accounts باستخدام provider_account_id[cite: 4]
    oauth_entry = (
        db.query(OAuthAccount)
        .filter(
            OAuthAccount.provider == OAuthProvider.GOOGLE,
            OAuthAccount.provider_account_id == google_account_id,
        )
        .first()
    )

    if oauth_entry:
        user = user_repo.get_by_id(oauth_entry.user_id)
    else:
        user = user_repo.get_by_email(email)

        if not user:
            user = user_repo.create_user(
                email=email,
                password_hash=None,
                role=UserRole.JOB_SEEKER,
            )
            user.is_verified = True
            db.commit()
            db.refresh(user)

            seeker_repo.create_profile(user_id=user.id)
        else:
            if not user.is_verified:
                user.is_verified = True
                db.commit()

        new_oauth = OAuthAccount(
            user_id=user.id,
            provider=OAuthProvider.GOOGLE,
            provider_account_id=google_account_id,
        )
        db.add(new_oauth)
        db.commit()

    # 3. إصدار توكن الدخول (Access Token)[cite: 4]
    access_token = create_access_token(
        data={
            "sub": str(user.id),
            "role": user.role.value if hasattr(user.role, "value") else str(user.role),
        }
    )

    return {
        "success": True,
        "message": "Google authentication successful",
        "access_token": access_token,
        "token_type": "bearer",
        "data": {
            "id": str(user.id),
            "email": user.email,
            "role": user.role.value if hasattr(user.role, "value") else str(user.role),
        },
    }

@router.post("/facebook", status_code=status.HTTP_200_OK)
def facebook_auth(request: FacebookLoginRequest, db: Session = Depends(get_db)):
    # 1. التحقق من التوكن عبر Facebook Graph API وجلب بيانات المستخدم
    # نطلب الحقول: id, email, name
    fb_graph_url = f"https://graph.facebook.com/me?fields=id,name,email&access_token={request.access_token}"
    
    try:
        response = httpx.get(fb_graph_url, timeout=10.0)
        if response.status_code != 200:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid or expired Facebook token"
            )
        fb_data = response.json()
    except httpx.RequestError:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Failed to communicate with Facebook servers"
        )

    fb_user_id = fb_data.get("id")
    email = fb_data.get("email")

    if not fb_user_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Unable to retrieve Facebook user identity"
        )

    # تنبيه: بعض حسابات فيسبوك مسجلة برقم هاتف فقط ولا تملك إيميل
    if not email:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Facebook account must have an email address associated with it"
        )

    user_repo = UserRepository(db)
    seeker_repo = SeekerRepository(db)

    # 2. البحث في جدول oauth_accounts باستخدام provider_account_id[cite: 4]
    oauth_entry = (
        db.query(OAuthAccount)
        .filter(
            OAuthAccount.provider == OAuthProvider.FACEBOOK,
            OAuthAccount.provider_account_id == fb_user_id,
        )
        .first()
    )

    if oauth_entry:
        user = user_repo.get_by_id(oauth_entry.user_id)
    else:
        # البحث بواسطة الإيميل لربط الحساب إذا كان مسجلاً مسبقاً[cite: 4]
        user = user_repo.get_by_email(email)

        if not user:
            # إنشاء مستخدم جديد وتفعيله تلقائياً[cite: 4]
            user = user_repo.create_user(
                email=email,
                password_hash=None,
                role=UserRole.JOB_SEEKER,
            )
            user.is_verified = True
            db.commit()
            db.refresh(user)

            seeker_repo.create_profile(user_id=user.id)
        else:
            if not user.is_verified:
                user.is_verified = True
                db.commit()

        new_oauth = OAuthAccount(
            user_id=user.id,
            provider=OAuthProvider.FACEBOOK,
            provider_account_id=fb_user_id,
        )
        db.add(new_oauth)
        db.commit()

    # 3. إصدار توكن الدخول (Access Token) الخاص بمنصتك[cite: 4]
    access_token = create_access_token(
        data={
            "sub": str(user.id),
            "role": user.role.value if hasattr(user.role, "value") else str(user.role),
        }
    )

    return {
        "success": True,
        "message": "Facebook authentication successful",
        "access_token": access_token,
        "token_type": "bearer",
        "data": {
            "id": str(user.id),
            "email": user.email,
            "role": user.role.value if hasattr(user.role, "value") else str(user.role),
        },
    }
@router.post("/linkedin", status_code=status.HTTP_200_OK)
def linkedin_auth(request: LinkedInLoginRequest, db: Session = Depends(get_db)):
    print("TOKEN RECEIVED FROM FRONTEND:", request.access_token)
    userinfo_url = "https://api.linkedin.com/v2/userinfo"
    headers = {"Authorization": f"Bearer {request.access_token}"}
    
    try:
        response = httpx.get(userinfo_url, headers=headers, timeout=10.0)
        if response.status_code != 200:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid or expired LinkedIn access token"
            )
        li_data = response.json()
    except httpx.RequestError:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Failed to communicate with LinkedIn servers"
        )

    li_user_id = li_data.get("sub")
    email = li_data.get("email")

    if not li_user_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Unable to retrieve LinkedIn user identity"
        )

    if not email:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="LinkedIn account must have an email address associated with it"
        )

    user_repo = UserRepository(db)
    seeker_repo = SeekerRepository(db)

    # 2. فحص جدول oauth_accounts
    oauth_entry = (
        db.query(OAuthAccount)
        .filter(
            OAuthAccount.provider == OAuthProvider.LINKEDIN,
            OAuthAccount.provider_account_id == li_user_id,
        )
        .first()
    )

    if oauth_entry:
        user = user_repo.get_by_id(oauth_entry.user_id)
    else:
        # البحث بواسطة البريد الإلكتروني لربط الحسابات المسجلة مسبقاً
        user = user_repo.get_by_email(email)

        if not user:
            # إنشاء حساب باحث عن عمل جديد موثق
            user = user_repo.create_user(
                email=email,
                password_hash=None,
                role=UserRole.JOB_SEEKER,
            )
            user.is_verified = True
            db.commit()
            db.refresh(user)

            seeker_repo.create_profile(user_id=user.id)
        else:
            if not user.is_verified:
                user.is_verified = True
                db.commit()

        # تسجيل الربط في oauth_accounts
        new_oauth = OAuthAccount(
            user_id=user.id,
            provider=OAuthProvider.LINKEDIN,
            provider_account_id=li_user_id,
        )
        db.add(new_oauth)
        db.commit()

    # 3. إصدار توكن المنصة الداخلي (JWT)
    access_token = create_access_token(
        data={
            "sub": str(user.id),
            "role": user.role.value if hasattr(user.role, "value") else str(user.role),
        }
    )

    return {
        "success": True,
        "message": "LinkedIn authentication successful",
        "access_token": access_token,
        "token_type": "bearer",
        "data": {
            "id": str(user.id),
            "email": user.email,
            "role": user.role.value if hasattr(user.role, "value") else str(user.role),
        },
    }