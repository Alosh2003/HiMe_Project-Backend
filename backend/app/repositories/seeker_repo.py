from sqlalchemy.orm import Session
from uuid import UUID
from typing import Optional
from app.models.job_seeker import JobSeeker

class SeekerRepository:
    def __init__(self, db: Session):
        self.db = db

    # 1. جلب بروفايل الباحث عن عمل باستخدام user_id
    def get_by_user_id(self, user_id: UUID) -> Optional[JobSeeker]:
        return self.db.query(JobSeeker).filter(JobSeeker.user_id == user_id).first()

    # 2. إنشاء بروفايل مبدئي عند التسجيل
    def create_profile(self, user_id: UUID) -> JobSeeker:
        seeker = JobSeeker(user_id=user_id)
        self.db.add(seeker)
        self.db.commit()
        self.db.refresh(seeker)
        return seeker

    # 3. تحديث بيانات الملف الشخصي (الاسم والهاتف)
    def update_profile(self, seeker: JobSeeker, first_name: str, last_name: str, phone: Optional[str] = None) -> JobSeeker:
        seeker.first_name = first_name
        seeker.last_name = last_name
        if phone:
            seeker.phone = phone
        self.db.commit()
        self.db.refresh(seeker)
        return seeker

    # 4. تحديث رابط الـ CV وحالتها
    def update_resume(self, seeker: JobSeeker, resume_url: str, resume_status: str = "pending") -> JobSeeker:
        seeker.resume_url = resume_url
        seeker.resume_status = resume_status
        self.db.commit()
        self.db.refresh(seeker)
        return seeker
    
    def update_profile(self, user_id: UUID, update_data: dict) -> Optional[JobSeeker]:
        """تحديث بيانات الملف الشخصي للباحث عن عمل"""
        seeker = self.get_by_user_id(user_id)
        if not seeker:
            return None
        
        # تحديث الحقول التي تم إرسالها فقط (تجاهل القيم فارغة None)
        for key, value in update_data.items():
            if value is not None:
                setattr(seeker, key, value)
                
        self.db.commit()
        self.db.refresh(seeker)
        return seeker