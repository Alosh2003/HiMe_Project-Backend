from datetime import date, datetime
from typing import List, Optional
from uuid import UUID
from pydantic import BaseModel, ConfigDict, Field
from app.schemas.response import BaseResponse
from app.models.company import WorkplaceType, JobEmploymentType, JobStatus

# ================= Company Profile Schemas =================
class CompanyBase(BaseModel):
    company_name: Optional[str] = Field(None, example="شركة التقنية الحديثة")
    vision: Optional[str] = Field(None, example="معاً نبني المستقبل")
    industry: Optional[str] = Field(None, example="حلول تقنية")
    location: Optional[str] = Field(None, example="حضرموت - اليمن")
    establishment_year: Optional[int] = Field(None, example=2018)
    website_url: Optional[str] = Field(None, example="https://techvision.ai")
    linkedin_url: Optional[str] = Field(None, example="https://linkedin.com/company/techvision")
    about: Optional[str] = Field(None, example="نحن في التقنية الحديثة نسعى لتمكين الشركات...")
    logo_url: Optional[str] = None
    cover_image_url: Optional[str] = None

class CompanyUpdate(CompanyBase):
    pass

class CompanyData(CompanyBase):
    id: UUID
    user_id: UUID
    created_at: datetime
    updated_at: datetime
    model_config = ConfigDict(from_attributes=True)

class ApiResponseCompany(BaseResponse):
    data: CompanyData

# ================= Job Skills Schemas =================
class JobSkillData(BaseModel):
    id: UUID
    skill_name: str
    model_config = ConfigDict(from_attributes=True)

# ================= Jobs Schemas =================
class JobBase(BaseModel):
    title: str = Field(..., max_length=150, example="UI/UX Designer")
    education_level: str = Field(..., example="بكالوريوس")
    field_of_study: str = Field(..., example="تصميم واجهات / تقنية معلومات")
    experience_years: int = Field(..., ge=0, example=2)
    location: str = Field(..., example="حضرموت - المكلا")
    workplace_type: WorkplaceType = Field(..., example=WorkplaceType.ON_SITE)
    employment_type: JobEmploymentType = Field(..., example=JobEmploymentType.FULL_TIME)
    application_deadline: date = Field(..., example="2026-08-28")
    description: str = Field(..., example="نبحث عن مصمم واجهات مبدع للعمل مع فريقنا...")
    post_image_url: Optional[str] = None

class JobCreate(JobBase):
    skills: List[str] = Field(..., example=["Figma", "UI/UX Designer", "Problem Solving", "Adobe XD"])

class JobUpdate(BaseModel):
    title: Optional[str] = None
    education_level: Optional[str] = None
    field_of_study: Optional[str] = None
    experience_years: Optional[int] = None
    location: Optional[str] = None
    workplace_type: Optional[WorkplaceType] = None
    employment_type: Optional[JobEmploymentType] = None
    application_deadline: Optional[date] = None
    description: Optional[str] = None
    post_image_url: Optional[str] = None
    status: Optional[JobStatus] = None
    skills: Optional[List[str]] = None

class JobData(JobBase):
    id: UUID
    company_id: UUID
    status: JobStatus
    skills: List[JobSkillData] = []
    created_at: datetime
    updated_at: datetime
    model_config = ConfigDict(from_attributes=True)

class ApiResponseJob(BaseResponse):
    data: JobData

class ApiResponseJobList(BaseResponse):
    data: List[JobData]