import io
from uuid import UUID
from pypdf import PdfReader
from sqlalchemy.orm import Session

from app.api.deps import RoleChecker
from app.core.cloudinary import cloudinary, uploader
from app.models.job_seeker import (
    Certification,
    Education,
    JobSeeker,
    Project,
    ProjectImage,
    SeekerSkill,
    WorkExperience,
)
from app.models.user import User
from app.repositories.seeker_repo import SeekerRepository
from app.schemas.response import BaseResponse, ErrorResponse
from app.schemas import seeker as schemas
from typing import Annotated, List
from typing import List
from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status, BackgroundTasks
from app.db.session import get_db, SessionLocal
from app.services.resume_processor import ResumeProcessorService
router = APIRouter(prefix="/seekers", tags=["Seekers"])

allow_seeker_only = RoleChecker(["job_seeker"])


def get_current_seeker(current_user: User, db: Session) -> JobSeeker:
    seeker = db.query(JobSeeker).filter(JobSeeker.user_id == current_user.id).first()
    if not seeker:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Seeker profile not found",
        )
    return seeker

def run_resume_processing_task(user_id: UUID, extracted_text: str | None):
    """جلسة مستقلة في الخلفية لتشغيل الـ AI وحفظ البيانات في Neon"""
    db = SessionLocal()
    try:
        processor = ResumeProcessorService(db)
        processor.process_and_save_resume(user_id=user_id, raw_text=extracted_text)
    finally:
        db.close()
# ==========================================
# 1. Profile Core & Resume
# ==========================================
@router.get(
    "/profile",
    response_model=schemas.ApiResponseProfile,
    status_code=status.HTTP_200_OK,
    responses={401: {"model": ErrorResponse}, 404: {"model": ErrorResponse}},
)
def get_profile(
    current_user: User = Depends(allow_seeker_only),
    db: Session = Depends(get_db),
):
    seeker_repo = SeekerRepository(db)
    seeker = seeker_repo.get_by_user_id(current_user.id)
    if not seeker:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Profile not found",
        )

    return schemas.ApiResponseProfile(
        message="Profile retrieved successfully",
        success=True,
        data=schemas.ProfileData.model_validate(seeker),
    )


@router.put(
    "/profile",
    response_model=schemas.ApiResponseProfile,
    status_code=status.HTTP_200_OK,
    responses={401: {"model": ErrorResponse}, 404: {"model": ErrorResponse}},
)
def update_seeker_profile(
    body: schemas.UpdateProfileRequest,
    current_user: User = Depends(allow_seeker_only),
    db: Session = Depends(get_db),
):
    seeker_repo = SeekerRepository(db)
    updated_seeker = seeker_repo.update_profile(
        user_id=current_user.id,
        update_data=body.model_dump(exclude_unset=True),
    )
    if not updated_seeker:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Seeker profile not found",
        )

    return schemas.ApiResponseProfile(
        success=True,
        message="Profile updated successfully",
        data=schemas.ProfileData.model_validate(updated_seeker),
    )


@router.patch(
    "/profile/about",
    response_model=schemas.ApiResponseProfile,
    status_code=status.HTTP_200_OK,
    responses={401: {"model": ErrorResponse}, 404: {"model": ErrorResponse}},
)
def update_about(
    data: schemas.AboutUpdate,
    current_user: User = Depends(allow_seeker_only),
    db: Session = Depends(get_db),
):
    seeker = get_current_seeker(current_user, db)
    seeker.about = data.about
    db.commit()
    db.refresh(seeker)
    return schemas.ApiResponseProfile(
        success=True,
        message="About section updated successfully",
        data=schemas.ProfileData.model_validate(seeker),
    )

@router.post(
    "/resume",
    response_model=BaseResponse,
    status_code=status.HTTP_200_OK,
    responses={400: {"model": ErrorResponse}, 404: {"model": ErrorResponse}},
)
async def upload_resume(
    background_tasks: BackgroundTasks,
    resume: UploadFile = File(...),
    current_user: User = Depends(allow_seeker_only),
    db: Session = Depends(get_db),
):
    seeker_repo = SeekerRepository(db)
    seeker = seeker_repo.get_by_user_id(current_user.id)
    if not seeker:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Job seeker profile not found for this user"
        )

    # 1. التحقق من امتداد وحجم الملف (الحد الأقصى 5MB)
    ALLOWED_EXTENSIONS = {".pdf", ".docx"}
    MAX_FILE_SIZE = 5 * 1024 * 1024

    filename = resume.filename
    file_ext = "" if not filename else ("." + filename.split('.')[-1]).lower()
    if file_ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(status_code=400, detail="Only PDF and DOCX files are allowed.")

    contents = await resume.read()
    if len(contents) > MAX_FILE_SIZE:
        raise HTTPException(status_code=400, detail="File size exceeds 5MB limit.")

    # 2. حذف الملف القديم من Cloudinary إن وجد
    if seeker.resume_url and "hime_resumes/" in seeker.resume_url:
        try:
            old_filename = seeker.resume_url.split("hime_resumes/")[-1].rsplit(".", 1)[0]
            cloudinary.uploader.destroy(f"hime_resumes/{old_filename}", resource_type="raw")
        except Exception:
            pass

    # 3. رفع الملف إلى Cloudinary
    bytes_io = io.BytesIO(contents)
    bytes_io.seek(0)
    try:
        upload_result = cloudinary.uploader.upload(
            bytes_io,
            resource_type="auto",
            folder="hime_resumes",
            unique_filename=True,
            overwrite=True
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to upload file to Cloudinary: {str(e)}")

    secure_url = upload_result.get("secure_url") or upload_result.get("url")

    # 4. استخراج النص من ملف الـ PDF
    extracted_text = None
    if file_ext == ".pdf":
        try:
            pdf_reader = PdfReader(io.BytesIO(contents))
            extracted_text = "".join((page.extract_text() or "") for page in pdf_reader.pages)
        except Exception:
            extracted_text = None

    # 5. حفظ الرابط وضبط الحالة فوراً إلى processing
    seeker.resume_url = secure_url
    seeker.resume_status = "processing"
    db.commit()
    db.refresh(seeker)

    # 6. إطلاق مهمة المعالجة الخلفية عبر الذكاء الاصطناعي
    background_tasks.add_task(
        run_resume_processing_task,
        user_id=current_user.id,
        extracted_text=extracted_text,
    )

    return BaseResponse(
        success=True,
        message="Resume uploaded successfully. Processing started in the background.",
        data={
            "resume_url": seeker.resume_url,
            "resume_status": seeker.resume_status
        }
    )

@router.get(
    "/resume/status",
    response_model=schemas.ApiResponseResumeStatus,
    status_code=status.HTTP_200_OK,
    responses={401: {"model": ErrorResponse}, 404: {"model": ErrorResponse}},
)
def get_resume_status(
    current_user: User = Depends(allow_seeker_only),
    db: Session = Depends(get_db),
):
    seeker_repo = SeekerRepository(db)
    seeker = seeker_repo.get_by_user_id(current_user.id)
    if not seeker:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Seeker profile not found",
        )

    return schemas.ApiResponseResumeStatus(
        success=True,
        message="Resume status retrieved successfully",
        data=schemas.ResumeStatusData(
            resume_status=seeker.resume_status,
            resume_url=seeker.resume_url,
        ),
    )


# ==========================================
# 2. Work Experiences
# ==========================================
@router.get(
    "/experiences",
    response_model=schemas.ApiResponseExperienceList,
    status_code=status.HTTP_200_OK,
)
def get_experiences(
    current_user: User = Depends(allow_seeker_only),
    db: Session = Depends(get_db),
):
    seeker = get_current_seeker(current_user, db)
    experiences = db.query(WorkExperience).filter(WorkExperience.profile_id == seeker.id).all()
    return schemas.ApiResponseExperienceList(
        success=True,
        message="Experiences retrieved successfully",
        data=[schemas.ExperienceData.model_validate(e) for e in experiences],
    )


@router.post(
    "/experiences",
    response_model=schemas.ApiResponseExperience,
    status_code=status.HTTP_201_CREATED,
)
def create_experience(
    data: schemas.ExperienceCreate,
    current_user: User = Depends(allow_seeker_only),
    db: Session = Depends(get_db),
):
    seeker = get_current_seeker(current_user, db)
    exp = WorkExperience(**data.model_dump(), profile_id=seeker.id)
    db.add(exp)
    db.commit()
    db.refresh(exp)
    return schemas.ApiResponseExperience(
        success=True,
        message="Experience created successfully",
        data=schemas.ExperienceData.model_validate(exp),
    )


@router.put(
    "/experiences/{id}",
    response_model=schemas.ApiResponseExperience,
    status_code=status.HTTP_200_OK,
)
def update_experience(
    id: UUID,
    data: schemas.ExperienceUpdate,
    current_user: User = Depends(allow_seeker_only),
    db: Session = Depends(get_db),
):
    seeker = get_current_seeker(current_user, db)
    exp = (
        db.query(WorkExperience)
        .filter(WorkExperience.id == id, WorkExperience.profile_id == seeker.id)
        .first()
    )
    if not exp:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Experience not found")

    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(exp, field, value)

    db.commit()
    db.refresh(exp)
    return schemas.ApiResponseExperience(
        success=True,
        message="Experience updated successfully",
        data=schemas.ExperienceData.model_validate(exp),
    )


@router.delete(
    "/experiences/{id}",
    response_model=BaseResponse,
    status_code=status.HTTP_200_OK,
)
def delete_experience(
    id: UUID,
    current_user: User = Depends(allow_seeker_only),
    db: Session = Depends(get_db),
):
    seeker = get_current_seeker(current_user, db)
    exp = (
        db.query(WorkExperience)
        .filter(WorkExperience.id == id, WorkExperience.profile_id == seeker.id)
        .first()
    )
    if not exp:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Experience not found")

    db.delete(exp)
    db.commit()
    return BaseResponse(success=True, message="Experience deleted successfully", data=None)


# ==========================================
# 3. Educations
# ==========================================
@router.get(
    "/educations",
    response_model=schemas.ApiResponseEducationList,
    status_code=status.HTTP_200_OK,
)
def get_educations(
    current_user: User = Depends(allow_seeker_only),
    db: Session = Depends(get_db),
):
    seeker = get_current_seeker(current_user, db)
    educations = db.query(Education).filter(Education.profile_id == seeker.id).all()
    return schemas.ApiResponseEducationList(
        success=True,
        message="Educations retrieved successfully",
        data=[schemas.EducationData.model_validate(e) for e in educations],
    )


@router.post(
    "/educations",
    response_model=schemas.ApiResponseEducation,
    status_code=status.HTTP_201_CREATED,
)
def create_education(
    data: schemas.EducationCreate,
    current_user: User = Depends(allow_seeker_only),
    db: Session = Depends(get_db),
):
    seeker = get_current_seeker(current_user, db)
    edu = Education(**data.model_dump(), profile_id=seeker.id)
    db.add(edu)
    db.commit()
    db.refresh(edu)
    return schemas.ApiResponseEducation(
        success=True,
        message="Education created successfully",
        data=schemas.EducationData.model_validate(edu),
    )


@router.put(
    "/educations/{id}",
    response_model=schemas.ApiResponseEducation,
    status_code=status.HTTP_200_OK,
)
def update_education(
    id: UUID,
    data: schemas.EducationUpdate,
    current_user: User = Depends(allow_seeker_only),
    db: Session = Depends(get_db),
):
    seeker = get_current_seeker(current_user, db)
    edu = (
        db.query(Education)
        .filter(Education.id == id, Education.profile_id == seeker.id)
        .first()
    )
    if not edu:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Education not found")

    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(edu, field, value)

    db.commit()
    db.refresh(edu)
    return schemas.ApiResponseEducation(
        success=True,
        message="Education updated successfully",
        data=schemas.EducationData.model_validate(edu),
    )


@router.delete(
    "/educations/{id}",
    response_model=BaseResponse,
    status_code=status.HTTP_200_OK,
)
def delete_education(
    id: UUID,
    current_user: User = Depends(allow_seeker_only),
    db: Session = Depends(get_db),
):
    seeker = get_current_seeker(current_user, db)
    edu = (
        db.query(Education)
        .filter(Education.id == id, Education.profile_id == seeker.id)
        .first()
    )
    if not edu:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Education not found")

    db.delete(edu)
    db.commit()
    return BaseResponse(success=True, message="Education deleted successfully", data=None)


# ==========================================
# 4. Projects
# ==========================================
@router.get(
    "/projects",
    response_model=schemas.ApiResponseProjectList,
    status_code=status.HTTP_200_OK,
)
def get_projects(
    current_user: User = Depends(allow_seeker_only),
    db: Session = Depends(get_db),
):
    seeker = get_current_seeker(current_user, db)
    projects = db.query(Project).filter(Project.profile_id == seeker.id).all()
    return schemas.ApiResponseProjectList(
        success=True,
        message="Projects retrieved successfully",
        data=[schemas.ProjectData.model_validate(p) for p in projects],
    )


@router.post(
    "/projects",
    response_model=schemas.ApiResponseProject,
    status_code=status.HTTP_201_CREATED,
)
def create_project(
    data: schemas.ProjectCreate,
    current_user: User = Depends(allow_seeker_only),
    db: Session = Depends(get_db),
):
    seeker = get_current_seeker(current_user, db)
    project_dict = data.model_dump(exclude={"image_urls"})
    project = Project(**project_dict, profile_id=seeker.id)
    db.add(project)
    db.commit()
    db.refresh(project)

    if data.image_urls:
        for url in data.image_urls:
            db.add(ProjectImage(project_id=project.id, image_url=url))
        db.commit()
        db.refresh(project)

    return schemas.ApiResponseProject(
        success=True,
        message="Project created successfully",
        data=schemas.ProjectData.model_validate(project),
    )


@router.put(
    "/projects/{id}",
    response_model=schemas.ApiResponseProject,
    status_code=status.HTTP_200_OK,
)
def update_project(
    id: UUID,
    data: schemas.ProjectUpdate,
    current_user: User = Depends(allow_seeker_only),
    db: Session = Depends(get_db),
):
    seeker = get_current_seeker(current_user, db)
    project = (
        db.query(Project)
        .filter(Project.id == id, Project.profile_id == seeker.id)
        .first()
    )
    if not project:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")

    update_dict = data.model_dump(exclude_unset=True, exclude={"image_urls"})
    for field, value in update_dict.items():
        setattr(project, field, value)

    if data.image_urls is not None:
        db.query(ProjectImage).filter(ProjectImage.project_id == project.id).delete()
        for url in data.image_urls:
            db.add(ProjectImage(project_id=project.id, image_url=url))

    db.commit()
    db.refresh(project)
    return schemas.ApiResponseProject(
        success=True,
        message="Project updated successfully",
        data=schemas.ProjectData.model_validate(project),
    )


@router.delete(
    "/projects/{id}",
    response_model=BaseResponse,
    status_code=status.HTTP_200_OK,
)
def delete_project(
    id: UUID,
    current_user: User = Depends(allow_seeker_only),
    db: Session = Depends(get_db),
):
    seeker = get_current_seeker(current_user, db)
    project = (
        db.query(Project)
        .filter(Project.id == id, Project.profile_id == seeker.id)
        .first()
    )
    if not project:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")

    db.delete(project)
    db.commit()
    return BaseResponse(success=True, message="Project deleted successfully", data=None)


# ==========================================
# 5. Certifications
# ==========================================
@router.get(
    "/certifications",
    response_model=schemas.ApiResponseCertificationList,
    status_code=status.HTTP_200_OK,
)
def get_certifications(
    current_user: User = Depends(allow_seeker_only),
    db: Session = Depends(get_db),
):
    seeker = get_current_seeker(current_user, db)
    certifications = db.query(Certification).filter(Certification.profile_id == seeker.id).all()
    return schemas.ApiResponseCertificationList(
        success=True,
        message="Certifications retrieved successfully",
        data=[schemas.CertificationData.model_validate(c) for c in certifications],
    )


@router.post(
    "/certifications",
    response_model=schemas.ApiResponseCertification,
    status_code=status.HTTP_201_CREATED,
)
def create_certification(
    data: schemas.CertificationCreate,
    current_user: User = Depends(allow_seeker_only),
    db: Session = Depends(get_db),
):
    seeker = get_current_seeker(current_user, db)
    cert = Certification(**data.model_dump(), profile_id=seeker.id)
    db.add(cert)
    db.commit()
    db.refresh(cert)
    return schemas.ApiResponseCertification(
        success=True,
        message="Certification created successfully",
        data=schemas.CertificationData.model_validate(cert),
    )


@router.put(
    "/certifications/{id}",
    response_model=schemas.ApiResponseCertification,
    status_code=status.HTTP_200_OK,
)
def update_certification(
    id: UUID,
    data: schemas.CertificationUpdate,
    current_user: User = Depends(allow_seeker_only),
    db: Session = Depends(get_db),
):
    seeker = get_current_seeker(current_user, db)
    cert = (
        db.query(Certification)
        .filter(Certification.id == id, Certification.profile_id == seeker.id)
        .first()
    )
    if not cert:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Certification not found"
        )

    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(cert, field, value)

    db.commit()
    db.refresh(cert)
    return schemas.ApiResponseCertification(
        success=True,
        message="Certification updated successfully",
        data=schemas.CertificationData.model_validate(cert),
    )


@router.delete(
    "/certifications/{id}",
    response_model=BaseResponse,
    status_code=status.HTTP_200_OK,
)
def delete_certification(
    id: UUID,
    current_user: User = Depends(allow_seeker_only),
    db: Session = Depends(get_db),
):
    seeker = get_current_seeker(current_user, db)
    cert = (
        db.query(Certification)
        .filter(Certification.id == id, Certification.profile_id == seeker.id)
        .first()
    )
    if not cert:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Certification not found"
        )

    db.delete(cert)
    db.commit()
    return BaseResponse(success=True, message="Certification deleted successfully", data=None)


# ==========================================
# 6. Skills
# ==========================================
@router.get(
    "/skills",
    response_model=schemas.ApiResponseSkillList,
    status_code=status.HTTP_200_OK,
)
def get_skills(
    current_user: User = Depends(allow_seeker_only),
    db: Session = Depends(get_db),
):
    seeker = get_current_seeker(current_user, db)
    skills = db.query(SeekerSkill).filter(SeekerSkill.profile_id == seeker.id).all()
    return schemas.ApiResponseSkillList(
        success=True,
        message="Skills retrieved successfully",
        data=[schemas.SkillData.model_validate(s) for s in skills],
    )


@router.post(
    "/skills",
    response_model=schemas.ApiResponseSkillList,
    status_code=status.HTTP_201_CREATED,
)
def add_skills(
    data: schemas.SkillsAddRequest,
    current_user: User = Depends(allow_seeker_only),
    db: Session = Depends(get_db),
):
    seeker = get_current_seeker(current_user, db)
    for skill in data.skills:
        clean_skill = skill.strip()
        if not clean_skill:
            continue
        existing = (
            db.query(SeekerSkill)
            .filter(
                SeekerSkill.profile_id == seeker.id,
                SeekerSkill.skill_name == clean_skill,
            )
            .first()
        )
        if not existing:
            db.add(SeekerSkill(profile_id=seeker.id, skill_name=clean_skill))
    db.commit()

    skills = db.query(SeekerSkill).filter(SeekerSkill.profile_id == seeker.id).all()
    return schemas.ApiResponseSkillList(
        success=True,
        message="Skills updated successfully",
        data=[schemas.SkillData.model_validate(s) for s in skills],
    )


@router.delete(
    "/skills/{id}",
    response_model=BaseResponse,
    status_code=status.HTTP_200_OK,
)
def delete_skill(
    id: UUID,
    current_user: User = Depends(allow_seeker_only),
    db: Session = Depends(get_db),
):
    seeker = get_current_seeker(current_user, db)
    skill = (
        db.query(SeekerSkill)
        .filter(SeekerSkill.id == id, SeekerSkill.profile_id == seeker.id)
        .first()
    )
    if not skill:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Skill not found")

    db.delete(skill)
    db.commit()
    return BaseResponse(success=True, message="Skill deleted successfully", data=None)


# ----------------- رفع صور المشاريع -----------------
@router.post(
    "/projects/upload-images",
    response_model=schemas.UploadMultipleImagesResponse,
    status_code=status.HTTP_200_OK,
)

async def upload_project_images_bulk(
    files: List[UploadFile] = File(..., media_type="multipart/form-data"),
    current_user: User = Depends(allow_seeker_only),
):
    ALLOWED_IMAGE_TYPES = {"image/jpeg", "image/png", "image/webp", "image/jpg"}
    uploaded_urls = []

    for file in files:
        if file.content_type not in ALLOWED_IMAGE_TYPES:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"File {file.filename} has unsupported format. Only JPEG, PNG, and WEBP are allowed."
            )

        contents = await file.read()
        if len(contents) > 5 * 1024 * 1024:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"File {file.filename} exceeds 5MB limit."
            )

        bytes_io = io.BytesIO(contents)
        bytes_io.seek(0)
        try:
            upload_result = cloudinary.uploader.upload(
                bytes_io,
                folder="hime_projects",
                resource_type="image",
                unique_filename=True,
            )
            secure_url = upload_result.get("secure_url") or upload_result.get("url")
            uploaded_urls.append(secure_url)
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to upload {file.filename}: {str(e)}"
            )

    return schemas.UploadMultipleImagesResponse(
        success=True,
        message="Images uploaded successfully",
        data=uploaded_urls
    )
# ----------------- رفع صور الشهادات -----------------
@router.post(
    "/certifications/upload-image",
    response_model=schemas.UploadImageResponse,
    status_code=status.HTTP_200_OK,
)
async def upload_certificate_image(
    file: UploadFile = File(...),
    current_user: User = Depends(allow_seeker_only),
):
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
            folder="hime_certificates",
            resource_type="image",
            unique_filename=True,
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to upload certificate image: {str(e)}"
        )

    return schemas.UploadImageResponse(
        success=True,
        message="Certificate image uploaded successfully",
        data={"image_url": upload_result.get("secure_url")}
    )