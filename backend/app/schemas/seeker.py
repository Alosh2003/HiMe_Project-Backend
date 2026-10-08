from datetime import date, datetime
from typing import List, Optional
from uuid import UUID
from pydantic import BaseModel, ConfigDict, Field
from app.schemas.response import BaseResponse
from app.models.job_seeker import EducationLevel, EmploymentType


# ----------------- 1. Core Profile & About -----------------
class UpdateProfileRequest(BaseModel):
    first_name: Optional[str] = Field(None, example="Ahmad")
    last_name: Optional[str] = Field(None, example="Ali")
    phone: Optional[str] = Field(None, example="+967770000000")


class AboutUpdate(BaseModel):
    about: str = Field(..., max_length=2000, example="مطور باك إند شغوف بالأنظمة السحابية...")


class ProfileData(BaseModel):
    id: UUID
    user_id: UUID
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    phone: Optional[str] = None
    resume_url: Optional[str] = None
    resume_status: str  # pending, processing, completed, failed
    about: Optional[str] = None  # تم إضافة حقل النبذة هنا
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ApiResponseProfile(BaseResponse):
    data: ProfileData


class ResumeStatusData(BaseModel):
    resume_status: str  # pending, processing, completed, failed
    resume_url: Optional[str] = None


class ApiResponseResumeStatus(BaseResponse):
    data: ResumeStatusData


# ----------------- 2. Work Experience -----------------
class ExperienceBase(BaseModel):
    job_title: str = Field(..., max_length=150, example="Backend Developer")
    company_name: str = Field(..., max_length=150, example="Tech Solutions")
    location: Optional[str] = Field(None, example="Riyadh, Saudi Arabia")
    employment_type: Optional[EmploymentType] = Field(None, example=EmploymentType.FULL_TIME)
    start_date: date
    end_date: Optional[date] = None
    is_current: bool = False
    description: str = Field(..., max_length=2000)


class ExperienceCreate(ExperienceBase):
    pass


class ExperienceUpdate(BaseModel):
    job_title: Optional[str] = Field(None, max_length=150)
    company_name: Optional[str] = Field(None, max_length=150)
    location: Optional[str] = None
    employment_type: Optional[EmploymentType] = None
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    is_current: Optional[bool] = None
    description: Optional[str] = Field(None, max_length=2000)


class ExperienceData(ExperienceBase):
    id: UUID
    model_config = ConfigDict(from_attributes=True)


class ApiResponseExperience(BaseResponse):
    data: ExperienceData


class ApiResponseExperienceList(BaseResponse):
    data: List[ExperienceData]


# ----------------- 3. Education -----------------
class EducationBase(BaseModel):
    degree: str = Field(..., max_length=100, example="Bachelor's degree")
    institution: str = Field(..., max_length=150, example="King Saud University")
    field_of_study: str = Field(..., max_length=150, example="Information Technology")
    location: Optional[str] = Field(None, example="Riyadh, Saudi Arabia")
    start_date: date
    graduation_date: date
    gpa: Optional[float] = Field(None, example=4.75)
    gpa_scale: Optional[str] = Field(None, example="5.0")
    current_level: EducationLevel = Field(..., example=EducationLevel.GRADUATE)
    description: Optional[str] = Field(None, max_length=1000)


class EducationCreate(EducationBase):
    pass


class EducationUpdate(BaseModel):
    degree: Optional[str] = Field(None, max_length=100)
    institution: Optional[str] = Field(None, max_length=150)
    field_of_study: Optional[str] = Field(None, max_length=150)
    location: Optional[str] = None
    start_date: Optional[date] = None
    graduation_date: Optional[date] = None
    gpa: Optional[float] = None
    gpa_scale: Optional[str] = None
    current_level: Optional[EducationLevel] = None
    description: Optional[str] = Field(None, max_length=1000)


class EducationData(EducationBase):
    id: UUID
    model_config = ConfigDict(from_attributes=True)


class ApiResponseEducation(BaseResponse):
    data: EducationData


class ApiResponseEducationList(BaseResponse):
    data: List[EducationData]


# ----------------- 4. Projects -----------------
class ProjectImageData(BaseModel):
    id: UUID
    image_url: str
    model_config = ConfigDict(from_attributes=True)


class ProjectBase(BaseModel):
    title: str = Field(..., max_length=150, example="Job Seeker Platform")
    project_type: Optional[str] = Field(None, example="Graduation Project")
    start_date: date
    end_date: Optional[date] = None
    description: str = Field(..., max_length=2000)
    project_url: Optional[str] = Field(None, example="https://myproject.com")
    github_url: Optional[str] = Field(None, example="https://github.com/myrepo")
    skills: List[str] = Field(default=[], example=["Python", "FastAPI", "PostgreSQL"])


class ProjectCreate(ProjectBase):
    image_urls: Optional[List[str]] = []


class ProjectUpdate(BaseModel):
    title: Optional[str] = Field(None, max_length=150)
    project_type: Optional[str] = None
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    description: Optional[str] = Field(None, max_length=2000)
    project_url: Optional[str] = None
    github_url: Optional[str] = None
    skills: Optional[List[str]] = None
    image_urls: Optional[List[str]] = None


class ProjectData(ProjectBase):
    id: UUID
    images: List[ProjectImageData] = []
    model_config = ConfigDict(from_attributes=True)


class ApiResponseProject(BaseResponse):
    data: ProjectData


class ApiResponseProjectList(BaseResponse):
    data: List[ProjectData]


# ----------------- 5. Certifications -----------------
class CertificationBase(BaseModel):
    title: str = Field(..., max_length=150, example="AWS Certified Cloud Practitioner")
    issuing_organization: str = Field(..., max_length=150, example="Amazon Web Services")
    location: Optional[str] = Field(None, example="Online")
    issue_date: date
    credential_id: Optional[str] = Field(None, example="AWS-123456")
    description: Optional[str] = None
    certificate_image_url: Optional[str] = None


class CertificationCreate(CertificationBase):
    pass


class CertificationUpdate(BaseModel):
    title: Optional[str] = Field(None, max_length=150)
    issuing_organization: Optional[str] = Field(None, max_length=150)
    location: Optional[str] = None
    issue_date: Optional[date] = None
    credential_id: Optional[str] = None
    description: Optional[str] = None
    certificate_image_url: Optional[str] = None


class CertificationData(CertificationBase):
    id: UUID
    model_config = ConfigDict(from_attributes=True)


class ApiResponseCertification(BaseResponse):
    data: CertificationData


class ApiResponseCertificationList(BaseResponse):
    data: List[CertificationData]


# ----------------- 6. Skills -----------------
class SkillsAddRequest(BaseModel):
    skills: List[str] = Field(..., example=["Docker", "FastAPI", "Redis"])


class SkillData(BaseModel):
    id: UUID
    skill_name: str
    model_config = ConfigDict(from_attributes=True)


class ApiResponseSkillList(BaseResponse):
    data: List[SkillData]
class UploadImageResponse(BaseResponse):
    data: dict  # {"image_url": "https://res.cloudinary.com/..."}
class UploadMultipleImagesResponse(BaseResponse):
    data: List[str]  # ["https://res.cloudinary.com/.../img1.png", "https://res.cloudinary.com/.../img2.png"]