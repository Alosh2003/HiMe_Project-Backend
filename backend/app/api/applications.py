from datetime import datetime
from typing import Optional
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from sqlalchemy import or_

from app.api.deps import RoleChecker, get_db
from app.models.user import User
from app.models.job_seeker import JobSeeker
from app.models.application import JobApplication
from app.models.company import Job  # تأكدي من مسار موديل الوظائف لديكِ
from app.schemas import application as schemas
from app.schemas.response import BaseResponse, ErrorResponse
from collections import Counter
from app.models.company import Company
router = APIRouter(tags=["Job Applications & Marketplace"])
allow_seeker_only = RoleChecker(["job_seeker"])


def get_current_seeker(current_user: User, db: Session) -> JobSeeker:
    seeker = db.query(JobSeeker).filter(JobSeeker.user_id == current_user.id).first()
    if not seeker:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Job seeker profile not found",
        )
    return seeker


# ==========================================
# 1. PB-11: استعراض الوظائف للباحث مع البحث والتحقق من التقديم
# ==========================================
@router.get(
    "/jobs/marketplace",
    response_model=BaseResponse,
    status_code=status.HTTP_200_OK,
)
def get_marketplace_jobs(
    search: Optional[str] = Query(None, description="البحث باسم الوظيفة أو الشركة"),
    page: int = Query(1, ge=1),
    limit: int = Query(10, ge=1, le=50),
    current_user: User = Depends(allow_seeker_only),
    db: Session = Depends(get_db),
):
    seeker = get_current_seeker(current_user, db)

    # 1. جلب معرفات الوظائف التي قدم عليها الباحث مسبقاً
    applied_job_ids = {
        app.job_id
        for app in db.query(JobApplication.job_id)
        .filter(JobApplication.seeker_id == seeker.id)
        .all()
    }

    # 2. Join jobs to their owning company.
    query = db.query(Job).outerjoin(Company, Job.company_id == Company.id)

    # 3. الفلترة المشتركة (اسم الوظيفة، وصفها، أو اسم الشركة)
    if search and search.strip():
        search_filter = f"%{search.strip()}%"
        query = query.filter(
            or_(
                Job.title.ilike(search_filter),
                Job.description.ilike(search_filter),
                Company.company_name.ilike(search_filter),  # البحث باسم الشركة
            )
        )

    # 4. جلب جميع الوظائف المطابقة لحساب المهارات الأكثر طلباً
    all_matched_jobs = query.order_by(Job.created_at.desc()).all()

    # 5. استخراج وحساب تكرار المهارات (Top Skills) بحد أقصى 10
    skills_counter = Counter()
    for job in all_matched_jobs:
        for skill in job.skills:
            if skill.skill_name:
                skills_counter[skill.skill_name.strip()] += 1

    top_skills = [skill for skill, _ in skills_counter.most_common(10)]

    # 6. تطبيق الترقيم (Pagination) على قائمة الوظائف المعروضة
    total = len(all_matched_jobs)
    offset = (page - 1) * limit
    paginated_jobs = all_matched_jobs[offset : offset + limit]

    items = []
    for job in paginated_jobs:
        company_name = (
            job.company.company_name
            if job.company and job.company.company_name
            else "Company"
        )
        job_skills = [skill.skill_name for skill in job.skills]

        items.append(
            schemas.MarketplaceJobItem(
                id=job.id,
                title=job.title,
                company_name=company_name,
                description=job.description,
                location=job.location,
                deadline=job.application_deadline,
                skills=job_skills,
                has_applied=(job.id in applied_job_ids),
                match_rate=75,
            )
        )

    total_pages = (total + limit - 1) // limit if total > 0 else 1

    return BaseResponse(
        success=True,
        message="Jobs retrieved successfully",
        data={
            "jobs": items,
            "top_skills": top_skills,
            "total": total,
            "page": page,
            "total_pages": total_pages,
        },
    )


# ==========================================
# 2. PB-13 & PB-14: التقديم بنقرة واحدة ومنع التكرار
# ==========================================
@router.post(
    "/applications",
    response_model=BaseResponse,
    status_code=status.HTTP_201_CREATED,
    responses={
        400: {"model": ErrorResponse},
        404: {"model": ErrorResponse},
        409: {"model": ErrorResponse, "description": "Duplicate application"},
    },
)
def apply_to_job(
    body: schemas.JobApplicationCreate,
    current_user: User = Depends(allow_seeker_only),
    db: Session = Depends(get_db),
):
    seeker = get_current_seeker(current_user, db)

    # 1. التحقق من وجود الوظيفة
    job = db.query(Job).filter(Job.id == body.job_id).first()
    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Job not found",
        )

    # 2. فحص مسبق لمنع التقديم المكرر (PB-14)
    existing_app = (
        db.query(JobApplication)
        .filter(
            JobApplication.job_id == body.job_id,
            JobApplication.seeker_id == seeker.id,
        )
        .first()
    )
    if existing_app:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="You have already applied for this job.",
        )

    # 3. إنشاء الطلب
    new_application = JobApplication(
        job_id=body.job_id,
        seeker_id=seeker.id,
        status="pending",
    )

    try:
        db.add(new_application)
        db.commit()
        db.refresh(new_application)
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="You have already applied for this job.",
        )

    return BaseResponse(
        success=True,
        message="Application submitted successfully",
        data={
            "application_id": new_application.id,
            "status": new_application.status,
            "applied_at": new_application.applied_at,
        },
    )


# ==========================================
# 3. عرض صفحة "طلباتي" مع الإحصائيات العلوية والترقيم
# ==========================================
@router.get(
    "/applications/my-applications",
    response_model=BaseResponse,
    status_code=status.HTTP_200_OK,
)
def get_my_applications(
    page: int = Query(1, ge=1),
    limit: int = Query(10, ge=1, le=50),
    current_user: User = Depends(allow_seeker_only),
    db: Session = Depends(get_db),
):
    seeker = get_current_seeker(current_user, db)

    # 1. حساب الإحصائيات العلوية لكامل طلبات الباحث
    all_apps = (
        db.query(JobApplication.status)
        .filter(JobApplication.seeker_id == seeker.id)
        .all()
    )

    total = len(all_apps)
    pending_count = sum(1 for a in all_apps if a.status in ["pending", "reviewed"])
    hired_count = sum(1 for a in all_apps if a.status in ["contact", "hired"])
    rejected_count = sum(1 for a in all_apps if a.status == "rejected")

    # 2. جلب الطلبات مع الترقيم
    offset = (page - 1) * limit
    paginated_apps = (
        db.query(JobApplication)
        .filter(JobApplication.seeker_id == seeker.id)
        .order_by(JobApplication.applied_at.desc())
        .offset(offset)
        .limit(limit)
        .all()
    )

    items = []
    for app in paginated_apps:
        company_name = app.job.company.company_name if app.job.company else "Company"

        items.append(
            schemas.SeekerApplicationItem(
                id=app.id,
                job_id=app.job_id,
                job_title=getattr(app.job, "title", "Job Title"),
                company_name=company_name,
                applied_at=app.applied_at,
                status=app.status,
                match_rate=75,
            )
        )

    total_pages = (total + limit - 1) // limit if total > 0 else 1

    return BaseResponse(
        success=True,
        message="Applications retrieved successfully",
        data=schemas.SeekerApplicationsResponseData(
            stats=schemas.ApplicationStats(
                total=total,
                pending=pending_count,
                hired=hired_count,
                rejected=rejected_count,
            ),
            applications=items,
            total_pages=total_pages,
            current_page=page,
        ).model_dump(),
    )