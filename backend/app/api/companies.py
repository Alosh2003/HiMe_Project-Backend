import io
from uuid import UUID
from typing import List
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, status
from sqlalchemy.orm import Session

from app.core.cloudinary import cloudinary  # ⬅️ استخدام نفس إعداد Cloudinary المركزي
from app.db.session import get_db
from app.models.user import User, UserRole
from app.repositories.company_repo import CompanyRepository
from app.schemas import company as schemas
from app.api.deps import get_current_user

router = APIRouter(prefix="/companies", tags=["Company Profile & Jobs"])

def allow_company_only(current_user: User = Depends(get_current_user)) -> User:
    if current_user.role != UserRole.COMPANY:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access restricted to company accounts only"
        )
    return current_user

# دالة مساعدة لرفع وفحص الصور
async def upload_image_to_cloudinary(file: UploadFile, folder_name: str) -> str:
    ALLOWED_IMAGE_TYPES = {"image/jpeg", "image/png", "image/webp", "image/jpg"}
    if file.content_type not in ALLOWED_IMAGE_TYPES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only JPEG, PNG, and WEBP image formats are supported."
        )

    contents = await file.read()
    if len(contents) > 5 * 1024 * 1024:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Image size exceeds 5MB limit."
        )

    bytes_io = io.BytesIO(contents)
    bytes_io.seek(0)
    try:
        upload_result = cloudinary.uploader.upload(
            bytes_io,
            folder=folder_name,
            resource_type="image",
            unique_filename=True,
        )
        return upload_result.get("secure_url") or upload_result.get("url")
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to upload image: {str(e)}"
        )


# ================= 1. إدارة ملف الشركة =================

@router.get("/profile", response_model=schemas.ApiResponseCompany)
def get_company_profile(
    db: Session = Depends(get_db),
    current_user: User = Depends(allow_company_only)
):
    repo = CompanyRepository(db)
    profile = repo.get_by_user_id(current_user.id)
    if not profile:
        profile = repo.create_company_profile(current_user.id)
    return {"success": True, "message": "Profile fetched successfully", "data": profile}

@router.put("/profile", response_model=schemas.ApiResponseCompany)
def update_company_profile(
    payload: schemas.CompanyUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(allow_company_only)
):
    repo = CompanyRepository(db)
    profile = repo.get_by_user_id(current_user.id)
    if not profile:
        profile = repo.create_company_profile(current_user.id)
    updated = repo.update_company(profile, payload)
    return {"success": True, "message": "Profile updated successfully", "data": updated}


# ================= 2. رفع صور الشركة (Logo & Cover) =================

@router.post("/profile/upload-logo", status_code=status.HTTP_200_OK)
async def upload_company_logo(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(allow_company_only)
):
    repo = CompanyRepository(db)
    profile = repo.get_by_user_id(current_user.id)
    if not profile:
        profile = repo.create_company_profile(current_user.id)

    # رفع الشعار إلى مجلد hime_companies/logos
    image_url = await upload_image_to_cloudinary(file, folder_name="hime_companies/logos")
    
    # حفظ الرابط فوراً في حقل logo_url
    profile.logo_url = image_url
    db.commit()
    db.refresh(profile)

    return {
        "success": True,
        "message": "Company logo uploaded and saved successfully",
        "data": {"logo_url": profile.logo_url}
    }

@router.post("/profile/upload-cover", status_code=status.HTTP_200_OK)
async def upload_company_cover(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(allow_company_only)
):
    repo = CompanyRepository(db)
    profile = repo.get_by_user_id(current_user.id)
    if not profile:
        profile = repo.create_company_profile(current_user.id)

    # رفع صورة الغلاف إلى مجلد hime_companies/covers
    image_url = await upload_image_to_cloudinary(file, folder_name="hime_companies/covers")
    
    # حفظ الرابط فوراً في حقل cover_image_url
    profile.cover_image_url = image_url
    db.commit()
    db.refresh(profile)

    return {
        "success": True,
        "message": "Company cover image uploaded and saved successfully",
        "data": {"cover_image_url": profile.cover_image_url}
    }


# ================= 3. إدارة الوظائف ورفع صورتها =================

@router.post("/jobs/upload-image", status_code=status.HTTP_200_OK)
async def upload_job_post_image(
    file: UploadFile = File(...),
    current_user: User = Depends(allow_company_only)
):
    # مسار لرفع صورة الإعلان قبل النشر وإرجاع الرابط ليتم تضمينه في post_image_url
    image_url = await upload_image_to_cloudinary(file, folder_name="hime_jobs")
    return {
        "success": True,
        "message": "Job image uploaded successfully",
        "data": {"post_image_url": image_url}
    }

@router.post("/jobs", response_model=schemas.ApiResponseJob, status_code=status.HTTP_201_CREATED)
def create_job_post(
    payload: schemas.JobCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(allow_company_only)
):
    repo = CompanyRepository(db)
    profile = repo.get_by_user_id(current_user.id)
    if not profile:
        profile = repo.create_company_profile(current_user.id)

    job = repo.create_job(company_id=profile.id, job_data=payload)
    return {"success": True, "message": "Job published successfully", "data": job}

@router.get("/jobs", response_model=schemas.ApiResponseJobList)
def list_company_jobs(
    db: Session = Depends(get_db),
    current_user: User = Depends(allow_company_only)
):
    repo = CompanyRepository(db)
    profile = repo.get_by_user_id(current_user.id)
    if not profile:
        return {"success": True, "message": "No jobs found", "data": []}

    jobs = repo.get_company_jobs(profile.id)
    return {"success": True, "message": "Jobs retrieved successfully", "data": jobs}

@router.put("/jobs/{job_id}", response_model=schemas.ApiResponseJob)
def edit_job_post(
    job_id: UUID,
    payload: schemas.JobUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(allow_company_only)
):
    repo = CompanyRepository(db)
    job = repo.get_job_by_id(job_id)
    if not job or job.company.user_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job not found")

    updated_job = repo.update_job(job, payload)
    return {"success": True, "message": "Job updated successfully", "data": updated_job}

@router.delete("/jobs/{job_id}", status_code=status.HTTP_200_OK)
def remove_job_post(
    job_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(allow_company_only)
):
    repo = CompanyRepository(db)
    job = repo.get_job_by_id(job_id)
    if not job or job.company.user_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job not found")

    repo.delete_job(job)
    return {"success": True, "message": "Job deleted successfully"}