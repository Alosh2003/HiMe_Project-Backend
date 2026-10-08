from uuid import UUID
from typing import Optional, List
from sqlalchemy.orm import Session
from app.models.company import Company, Job, JobSkill, JobStatus
from app.schemas.company import CompanyUpdate, JobCreate, JobUpdate

class CompanyRepository:
    def __init__(self, db: Session):
        self.db = db

    # ================= Company Profile =================
    def get_by_user_id(self, user_id: UUID) -> Optional[Company]:
        return self.db.query(Company).filter(Company.user_id == user_id).first()

    def get_by_id(self, company_id: UUID) -> Optional[Company]:
        return self.db.query(Company).filter(Company.id == company_id).first()

    def create_company_profile(self, user_id: UUID) -> Company:
        company = Company(user_id=user_id)
        self.db.add(company)
        self.db.commit()
        self.db.refresh(company)
        return company

    def update_company(self, company: Company, update_data: CompanyUpdate) -> Company:
        update_dict = update_data.model_dump(exclude_unset=True)
        for key, value in update_dict.items():
            setattr(company, key, value)
        self.db.commit()
        self.db.refresh(company)
        return company

    # ================= Jobs =================
    def create_job(self, company_id: UUID, job_data: JobCreate) -> Job:
        job_dict = job_data.model_dump(exclude={"skills"})
        job = Job(**job_dict, company_id=company_id)
        self.db.add(job)
        self.db.flush()

        # إضافة المهارات إلى جدول job_skills
        for skill_name in job_data.skills:
            clean_skill = skill_name.strip()
            if clean_skill:
                skill = JobSkill(job_id=job.id, skill_name=clean_skill)
                self.db.add(skill)

        self.db.commit()
        self.db.refresh(job)
        return job

    def get_job_by_id(self, job_id: UUID) -> Optional[Job]:
        return self.db.query(Job).filter(Job.id == job_id).first()

    def get_company_jobs(self, company_id: UUID) -> List[Job]:
        return self.db.query(Job).filter(Job.company_id == company_id).order_by(Job.created_at.desc()).all()

    def update_job(self, job: Job, job_data: JobUpdate) -> Job:
        update_dict = job_data.model_dump(exclude_unset=True, exclude={"skills"})
        for key, value in update_dict.items():
            setattr(job, key, value)

        # تحديث المهارات إذا تم تمريرها
        if job_data.skills is not None:
            self.db.query(JobSkill).filter(JobSkill.job_id == job.id).delete()
            for skill_name in job_data.skills:
                clean_skill = skill_name.strip()
                if clean_skill:
                    self.db.add(JobSkill(job_id=job.id, skill_name=clean_skill))

        self.db.commit()
        self.db.refresh(job)
        return job

    def delete_job(self, job: Job) -> None:
        self.db.delete(job)
        self.db.commit()