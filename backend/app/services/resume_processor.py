import os
import time
from datetime import date, datetime
from typing import List, Optional
from uuid import UUID
from dateutil import parser as date_parser
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
from google import genai
from google.genai import types

from app.models.job_seeker import (
    Education,
    EducationLevel,
    JobSeeker,
    SeekerSkill,
    WorkExperience,
)
from app.repositories.seeker_repo import SeekerRepository

# ==========================================
# 1. Pydantic Schemas لبناء الرد المهيكل
# ==========================================
class ParsedExperience(BaseModel):
    company_name: Optional[str] = Field(default=None, description="اسم الشركة أو المؤسسة")
    job_title: Optional[str] = Field(default=None, description="المسمى الوظيفي")
    location: Optional[str] = Field(default=None, description="مكان العمل إن وجد")
    start_date: Optional[str] = Field(default=None, description="تاريخ البدء بصيغة YYYY-MM-DD")
    end_date: Optional[str] = Field(default=None, description="تاريخ الانتهاء بصيغة YYYY-MM-DD")
    is_current: Optional[bool] = Field(default=None, description="هل الوظيفة الحالية مستمرة")
    description: Optional[str] = Field(default=None, description="ملخص المهام والمسؤوليات")

class ParsedEducation(BaseModel):
    institution: Optional[str] = Field(default=None, description="اسم المؤسسة التعليمية")
    degree: Optional[str] = Field(default=None, description="الدرجة العلمية")
    field_of_study: Optional[str] = Field(default=None, description="مجال الدراسة")
    location: Optional[str] = Field(default=None, description="مكان المؤسسة")
    start_date: Optional[str] = Field(default=None, description="تاريخ البدء بصيغة YYYY-MM-DD")
    graduation_date: Optional[str] = Field(default=None, description="تاريخ التخرج بصيغة YYYY-MM-DD")
    current_level: Optional[str] = Field(default=None, description="student or graduate")
    description: Optional[str] = Field(default=None, description="معلومات إضافية")

class ResumeParsedData(BaseModel):
    about: Optional[str] = Field(default=None, description="نبذة مهنية موجزة")
    skills: List[str] = Field(default_factory=list, description="قائمة بالمهارات الفردية")
    experiences: List[ParsedExperience] = Field(default_factory=list, description="قائمة بالخبرات")
    educations: List[ParsedEducation] = Field(default_factory=list, description="المؤهلات التعليمية")


_FALLBACK_START_DATE = date(2020, 1, 1)


def _bounded_text(value: Optional[str], fallback: str, max_length: int) -> str:
    cleaned = value.strip() if isinstance(value, str) else ""
    return (cleaned or fallback)[:max_length]


def _is_current_date(value: Optional[str]) -> bool:
    return isinstance(value, str) and value.strip().casefold() in {
        "current",
        "currently",
        "now",
        "ongoing",
        "present",
        "to date",
    }


def _parse_resume_date(value: Optional[str], fallback: date) -> date:
    if isinstance(value, date) and not isinstance(value, datetime):
        return value
    if not isinstance(value, str) or not value.strip() or _is_current_date(value):
        return fallback
    try:
        return date_parser.parse(
            value.strip(), default=datetime.combine(fallback, datetime.min.time())
        ).date()
    except (OverflowError, TypeError, ValueError):
        return fallback


def _parse_education_level(value: Optional[str]) -> EducationLevel:
    normalized = value.strip().casefold().replace("_", " ").replace("-", " ") if value else ""
    if normalized in {"student", "studying", "enrolled", "currently enrolled", "currently studying", "in progress"}:
        return EducationLevel.STUDENT
    return EducationLevel.GRADUATE


def _graduation_fallback(start_date: date) -> date:
    try:
        return start_date.replace(year=start_date.year + 4)
    except ValueError:
        return start_date.replace(year=start_date.year + 4, day=28)


# ==========================================
# 2. فئة خدمة معالجة وتحليل السيرة الذاتية
# ==========================================
class ResumeProcessorService:
    def __init__(self, db: Session):
        self.db = db
        self.seeker_repo = SeekerRepository(db)
        api_key = os.getenv("GEMINI_API_KEY")
        self.client = genai.Client(api_key=api_key) if api_key else None

    def parse_text_with_gemini(self, text: str) -> Optional[ResumeParsedData]:
        """إرسال النص إلى Gemini بالنماذج المعتمدة حصراً مع فترات انتظار كافية لتجاوز 503"""
        if not self.client or not text.strip():
            return None

        # تقليص النص لأول 8000 حرف لضمان استجابة سريعة جداً وتفادي حمل الخوادم
        truncated_text = text.strip()[:8000]

        prompt = f"""
        You are an expert HR and recruitment parser.
        Extract professional background from this resume into the given JSON schema.
        Ensure dates are in YYYY-MM-DD format if available.
        Clean and isolate technical and professional skills as separate strings.

        Resume Text:
        {truncated_text}
        """

        # النماذج المعتمدة والمدعومة حالياً فقط
        candidate_models = [
            "gemini-3.8-flash",
            "gemini-3.5-flash",
        ]

        for model_name in candidate_models:
            # 3 محاولات لكل نموذج مع تدرج زمني أطول
            for attempt in range(1, 4):
                try:
                    response = self.client.models.generate_content(
                        model=model_name,
                        contents=prompt,
                        config=types.GenerateContentConfig(
                            response_mime_type="application/json",
                            response_schema=ResumeParsedData,
                            temperature=0.1,
                        ),
                    )
                    return ResumeParsedData.model_validate_json(response.text)
                except Exception as e:
                    err = str(e)
                    print(f"[Gemini Error: {model_name} (Attempt {attempt})]: {err}")
                    
                    # إذا كان الخطأ ضغط مؤقت 503 ننتظر وقتاً كافياً (3 ثوانٍ، ثم 6 ثوانٍ)
                    if "503" in err or "UNAVAILABLE" in err:
                        wait_time = attempt * 3
                        time.sleep(wait_time)
                        continue
                    
                    # إذا كان الخطأ غير 503 ننتقل للموديل التالي فوراً
                    break

        return None

    def process_and_save_resume(self, user_id: UUID, raw_text: Optional[str]) -> bool:
        """تحليل النص واستبدال البيانات القديمة بالسيرة الجديدة كلياً دون تراكم"""
        seeker = self.seeker_repo.get_by_user_id(user_id)
        if not seeker:
            return False

        if not raw_text or not raw_text.strip():
            seeker.resume_status = "failed"
            self.db.commit()
            return False

        parsed_data = self.parse_text_with_gemini(raw_text)
        if not parsed_data:
            seeker.resume_status = "failed"
            self.db.commit()
            return False

        try:
            # 1. تحديث النبذة التعريفية
            if parsed_data.about:
                seeker.about = parsed_data.about

            # -------------------------------------------------------------
            # تنظيف واستبدال البيانات السابقة للمستخدم لمنع التراكم
            # -------------------------------------------------------------
            self.db.query(SeekerSkill).filter(SeekerSkill.profile_id == seeker.id).delete()
            self.db.query(WorkExperience).filter(WorkExperience.profile_id == seeker.id).delete()
            self.db.query(Education).filter(Education.profile_id == seeker.id).delete()

            # 2. إضافة المهارات المستخرجة من السيرة الجديدة
            unique_skills = set()
            for skill_name in parsed_data.skills:
                if not isinstance(skill_name, str):
                    continue
                clean_skill = skill_name.strip()[:100]
                if clean_skill and clean_skill.casefold() not in unique_skills:
                    unique_skills.add(clean_skill.casefold())
                    self.db.add(SeekerSkill(profile_id=seeker.id, skill_name=clean_skill))

            # 3. إضافة الخبرات العملية الجديدة
            for exp in parsed_data.experiences:
                is_current = bool(exp.is_current) or _is_current_date(exp.end_date)
                end_date = None
                if not is_current and exp.end_date and not _is_current_date(exp.end_date):
                    end_date = _parse_resume_date(exp.end_date, _FALLBACK_START_DATE)

                self.db.add(WorkExperience(
                    profile_id=seeker.id,
                    company_name=_bounded_text(exp.company_name, "Not specified", 150),
                    job_title=_bounded_text(exp.job_title, "Not specified", 150),
                    location=_bounded_text(exp.location, "", 150) or None,
                    description=_bounded_text(exp.description, "Not provided", 2000),
                    start_date=_parse_resume_date(exp.start_date, _FALLBACK_START_DATE),
                    end_date=end_date,
                    is_current=is_current,
                ))

            # 4. إضافة التعليم الجديد
            for edu in parsed_data.educations:
                start_date = _parse_resume_date(edu.start_date, _FALLBACK_START_DATE)
                graduation_fallback = _graduation_fallback(start_date)
                graduation_date = _parse_resume_date(edu.graduation_date, graduation_fallback)
                if graduation_date < start_date:
                    graduation_date = start_date

                self.db.add(Education(
                    profile_id=seeker.id,
                    institution=_bounded_text(edu.institution, "Not specified", 150),
                    degree=_bounded_text(edu.degree, "Not specified", 100),
                    field_of_study=_bounded_text(edu.field_of_study, "Not specified", 150),
                    location=_bounded_text(edu.location, "", 150) or None,
                    start_date=start_date,
                    graduation_date=graduation_date,
                    current_level=_parse_education_level(edu.current_level),
                    description=_bounded_text(edu.description, "", 1000) or None,
                ))

            # 5. اعتماد المعاملة وتحديث الحالة إلى مكتمل
            seeker.resume_status = "completed"
            self.db.commit()
            self.db.refresh(seeker)
            return True

        except Exception as e:
            self.db.rollback()
            print(f"[Database Save Error]: {str(e)}")
            seeker.resume_status = "failed"
            self.db.commit()
            return False