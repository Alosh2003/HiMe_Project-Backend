import re

from pydantic import BaseModel, EmailStr, field_validator
from uuid import UUID
from app.schemas.response import BaseResponse
from pydantic import BaseModel, EmailStr
from app.models.user import UserRole  
# شروط طلب التسجيل: POST /auth/register

def validate_password_strength(v: str) -> str:
    if len(v) < 8:
        raise ValueError("Password must be at least 8 characters long")
    if not re.search(r"[A-Z]", v):
        raise ValueError("Password must contain at least one uppercase letter (A-Z)")
    if not re.search(r"\d", v):
        raise ValueError("Password must contain at least one digit (0-9)")
    if not re.search(r"[!@#$%^&*(),.?\":{}|<>]", v):
        raise ValueError("Password must contain at least one special character")
    return v
class RegisterRequest(BaseModel):
    email: EmailStr
    password: str
    role: UserRole = UserRole.JOB_SEEKER 

    @field_validator("password")
    @classmethod
    def check_password(cls, v: str) -> str:
        return validate_password_strength(v)
class ForgotPasswordRequest(BaseModel):
    email: EmailStr

# نموذج إعادة تعيين كلمة المرور
class VerifyResetCodeRequest(BaseModel):
    email: EmailStr
    code: str

# 2. تعيين كلمة المرور الجديدة باستخدام التوكن المؤقت
class SetNewPasswordRequest(BaseModel):
    reset_token: str
    new_password: str

    @field_validator("new_password")
    @classmethod
    def check_new_password(cls, v: str) -> str:
        return validate_password_strength(v)
# شروط طلب تسجيل الدخول: POST /auth/login
class LoginRequest(BaseModel):
    email: EmailStr
    password: str

# شكل بيانات المستخدم الحسابية المرجعة
class UserObject(BaseModel):
    id: UUID
    email: EmailStr
    role: str

# الرد الموحد عند نجاح التسجيل[cite: 2]
class ApiResponseUser(BaseResponse):
    data: UserObject

# الرد الموحد عند نجاح تسجيل الدخول (يتضمن الـ access_token)[cite: 2]
class ApiResponseLogin(BaseResponse):
    data: dict
class TokenData(BaseModel):
    access_token: str
    token_type: str = "Bearer"
    user: UserObject
class VerifyEmailRequest(BaseModel):
    email: EmailStr
    code: str
class GoogleLoginRequest(BaseModel):
    id_token: str
from pydantic import BaseModel

class FacebookLoginRequest(BaseModel):
    access_token: str
class LinkedInLoginRequest(BaseModel):
    access_token: str