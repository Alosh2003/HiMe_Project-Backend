from datetime import date, datetime
from typing import List, Optional, Union
from uuid import UUID
from pydantic import BaseModel


# 1. مخطط إرسال طلب التقديم
class JobApplicationCreate(BaseModel):
    job_id: UUID


# 2. بطاقة الوظيفة في واجهة "الوظائف" (مع التحقق من التقديم المسبق)
class MarketplaceJobItem(BaseModel):
    id: UUID
    title: str
    company_name: str
    description: Optional[str] = None
    location: Optional[str] = None
    deadline: Optional[Union[datetime, date]] = None
    skills: List[str] = []
    has_applied: bool = False  # يُستخدم لتعطيل الزر وإظهار "تم التقديم على هذه الوظيفة"
    match_rate: Optional[int] = 75  # مساحة محجوزة لنسبة المطابقة (للسبرنت القادم)


# 3. إحصائيات لوحة التحكم في صفحة "طلباتي"
class ApplicationStats(BaseModel):
    total: int
    pending: int
    hired: int
    rejected: int


# 4. عنصر جدول التقديم في صفحة "طلباتي"
class SeekerApplicationItem(BaseModel):
    id: UUID
    job_id: UUID
    job_title: str
    company_name: str
    applied_at: datetime
    status: str  # pending, reviewed, contact, hired, rejected
    match_rate: Optional[int] = 75


# 5. استجابة صفحة "طلباتي" الكاملة مع الترقيم
class SeekerApplicationsResponseData(BaseModel):
    stats: ApplicationStats
    applications: List[SeekerApplicationItem]
    total_pages: int
    current_page: int
class MarketplaceResponseData(BaseModel):
    jobs: List[MarketplaceJobItem]
    top_skills: List[str]  # قائمة أكثر 10 مهارات تكراراً
    total: int
    page: int
    total_pages: int