import uuid
import enum
from sqlalchemy import (
    Column, String, Text, Integer, Date, ForeignKey,
    TIMESTAMP, Enum, UniqueConstraint, UUID
)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.db.base import Base

class WorkplaceType(str, enum.Enum):
    ON_SITE = "on_site"       # حضوري
    REMOTE = "remote"         # عن بعد
    HYBRID = "hybrid"         # هجين

class JobEmploymentType(str, enum.Enum):
    FULL_TIME = "full_time"   # دوام كامل
    PART_TIME = "part_time"   # دوام جزئي
    CONTRACT = "contract"     # عقد
    INTERNSHIP = "internship" # تدريب

class JobStatus(str, enum.Enum):
    ACTIVE = "active"
    CLOSED = "closed"
    DRAFT = "draft"

class Company(Base):
    __tablename__ = "companies"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, unique=True)
    
    company_name = Column(String(150), nullable=True)
    vision = Column(String(255), nullable=True)           # مثل: معاً نبني المستقبل
    industry = Column(String(150), nullable=True)         # الخدمة المقدمة: حلول تقنية
    location = Column(String(150), nullable=True)         # المدينة / الدولة
    establishment_year = Column(Integer, nullable=True)   # سنة التأسيس
    website_url = Column(String(255), nullable=True)
    linkedin_url = Column(String(255), nullable=True)
    about = Column(Text, nullable=True)
    logo_url = Column(String(500), nullable=True)
    cover_image_url = Column(String(500), nullable=True)

    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now())
    updated_at = Column(TIMESTAMP(timezone=True), server_default=func.now(), onupdate=func.now())

    # العلاقات
    user = relationship("User", back_populates="company_profile")
    jobs = relationship("Job", back_populates="company", cascade="all, delete-orphan")

class Job(Base):
    __tablename__ = "jobs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    company_id = Column(UUID(as_uuid=True), ForeignKey("companies.id", ondelete="CASCADE"), nullable=False, index=True)
    
    title = Column(String(150), nullable=False)
    education_level = Column(String(100), nullable=False)
    field_of_study = Column(String(150), nullable=False)
    experience_years = Column(Integer, nullable=False, default=0)
    location = Column(String(150), nullable=False)
    workplace_type = Column(Enum(WorkplaceType, name="workplace_type_enum"), nullable=False)
    employment_type = Column(Enum(JobEmploymentType, name="job_employment_type_enum"), nullable=False)
    application_deadline = Column(Date, nullable=False)
    description = Column(Text, nullable=False)
    post_image_url = Column(String(500), nullable=True)
    status = Column(Enum(JobStatus, name="job_status_enum"), default=JobStatus.ACTIVE, nullable=False)

    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now())
    updated_at = Column(TIMESTAMP(timezone=True), server_default=func.now(), onupdate=func.now())

    # العلاقات
    company = relationship("Company", back_populates="jobs")
    skills = relationship("JobSkill", back_populates="job", cascade="all, delete-orphan")

class JobSkill(Base):
    __tablename__ = "job_skills"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    job_id = Column(UUID(as_uuid=True), ForeignKey("jobs.id", ondelete="CASCADE"), nullable=False, index=True)
    skill_name = Column(String(100), nullable=False)

    __table_args__ = (
        UniqueConstraint("job_id", "skill_name", name="uq_job_skill"),
    )

    job = relationship("Job", back_populates="skills")