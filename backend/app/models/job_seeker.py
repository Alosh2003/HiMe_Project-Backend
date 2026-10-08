import uuid
import enum
from sqlalchemy import (
    Column, DateTime, String, Text, Boolean, Date, Numeric,
    ForeignKey, Enum, TIMESTAMP, UniqueConstraint, UUID, JSON
)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.db.base import Base

class EmploymentType(str, enum.Enum):
    FULL_TIME = "full_time"
    PART_TIME = "part_time"
    CONTRACT = "contract"
    INTERNSHIP = "internship"
    FREELANCE = "freelance"

class EducationLevel(str, enum.Enum):
    STUDENT = "student"
    GRADUATE = "graduate"

class JobSeeker(Base):
    __tablename__ = "job_seekers"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, unique=True)    
    first_name = Column(String, nullable=True)
    last_name = Column(String, nullable=True)
    phone = Column(String, nullable=True)
    resume_url = Column(String, nullable=True)
    resume_status = Column(String, default="pending", nullable=False)
    cv_embedding = Column(String, nullable=True) 
    about = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # Relationships
    user = relationship("User", back_populates="seeker_profile")
    experiences = relationship("WorkExperience", backref="seeker", cascade="all, delete-orphan")
    educations = relationship("Education", backref="seeker", cascade="all, delete-orphan")
    projects = relationship("Project", backref="seeker", cascade="all, delete-orphan")
    certifications = relationship("Certification", backref="seeker", cascade="all, delete-orphan")
    skills = relationship("SeekerSkill", backref="seeker", cascade="all, delete-orphan")

class WorkExperience(Base):
    __tablename__ = "work_experiences"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    profile_id = Column(UUID(as_uuid=True), ForeignKey("job_seekers.id", ondelete="CASCADE"), nullable=False, index=True)
    job_title = Column(String(150), nullable=False)
    company_name = Column(String(150), nullable=False)
    location = Column(String(150), nullable=True)
    employment_type = Column(Enum(EmploymentType, name="employment_type_enum"), nullable=True)
    start_date = Column(Date, nullable=False)
    end_date = Column(Date, nullable=True)
    is_current = Column(Boolean, default=False, nullable=False)
    description = Column(String(2000), nullable=False)
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now())
    updated_at = Column(TIMESTAMP(timezone=True), server_default=func.now(), onupdate=func.now())

class Education(Base):
    __tablename__ = "educations"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    profile_id = Column(UUID(as_uuid=True), ForeignKey("job_seekers.id", ondelete="CASCADE"), nullable=False, index=True)
    degree = Column(String(100), nullable=False)
    institution = Column(String(150), nullable=False)
    field_of_study = Column(String(150), nullable=False)
    location = Column(String(150), nullable=True)
    start_date = Column(Date, nullable=False)
    graduation_date = Column(Date, nullable=False)
    gpa = Column(Numeric(4, 2), nullable=True)
    gpa_scale = Column(String(20), nullable=True)
    current_level = Column(Enum(EducationLevel, name="education_level_enum"), nullable=False)
    description = Column(String(1000), nullable=True)
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now())
    updated_at = Column(TIMESTAMP(timezone=True), server_default=func.now(), onupdate=func.now())

class Project(Base):
    __tablename__ = "projects"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    profile_id = Column(UUID(as_uuid=True), ForeignKey("job_seekers.id", ondelete="CASCADE"), nullable=False, index=True)
    title = Column(String(150), nullable=False)
    project_type = Column(String(100), nullable=True)
    start_date = Column(Date, nullable=False)
    end_date = Column(Date, nullable=True)
    description = Column(String(2000), nullable=False)
    project_url = Column(String(500), nullable=True)
    github_url = Column(String(500), nullable=True)
    skills = Column(JSON, nullable=False, default=list)
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now())
    updated_at = Column(TIMESTAMP(timezone=True), server_default=func.now(), onupdate=func.now())

    images = relationship("ProjectImage", backref="project", cascade="all, delete-orphan")

class ProjectImage(Base):
    __tablename__ = "project_images"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    project_id = Column(UUID(as_uuid=True), ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, index=True)
    image_url = Column(String(500), nullable=False)
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now())

class Certification(Base):
    __tablename__ = "certifications"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    profile_id = Column(UUID(as_uuid=True), ForeignKey("job_seekers.id", ondelete="CASCADE"), nullable=False, index=True)
    title = Column(String(150), nullable=False)
    issuing_organization = Column(String(150), nullable=False)
    location = Column(String(150), nullable=True)
    issue_date = Column(Date, nullable=False)
    credential_id = Column(String(150), nullable=True)
    description = Column(Text, nullable=True)
    certificate_image_url = Column(String(500), nullable=True)
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now())
    updated_at = Column(TIMESTAMP(timezone=True), server_default=func.now(), onupdate=func.now())

class SeekerSkill(Base):
    __tablename__ = "seeker_skills"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    profile_id = Column(UUID(as_uuid=True), ForeignKey("job_seekers.id", ondelete="CASCADE"), nullable=False, index=True)
    skill_name = Column(String(100), nullable=False)

    __table_args__ = (
        UniqueConstraint("profile_id", "skill_name", name="uq_seeker_skill"),
    )