"""
AI Matching API Endpoints
=========================
REST API for AI-powered candidate-job matching.
Connected to database via repositories.
"""

import logging
from datetime import date
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.api.deps import RoleChecker, get_current_user
from app.db.session import get_db
from app.services.ai.embedding_service import EmbeddingService
from app.services.ai.matching_service import MatchingService
from app.repositories.embedding_repo import EmbeddingRepository
from app.repositories.company_repo import CompanyRepository
from app.models.job_seeker import JobSeeker
from app.models.company import Job, JobStatus
from app.models.user import User

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/ai", tags=["AI Matching"])
allow_seeker_only = RoleChecker(["job_seeker"])
allow_company_only = RoleChecker(["company"])


def get_embedding_service():
    """Dependency to get embedding service."""
    return EmbeddingService()


def get_matching_service(
    embedding_service: EmbeddingService = Depends(get_embedding_service),
):
    """Dependency to get matching service."""
    return MatchingService(embedding_service)


def _build_seeker_data(db: Session, seeker: JobSeeker) -> dict:
    """Build a data dict from a JobSeeker ORM object."""
    skills = [s.skill_name for s in seeker.skills]
    experience = [
        {
            "title": exp.job_title,
            "company": exp.company_name,
            "description": exp.description,
            "years": _calc_years(exp.start_date, exp.end_date),
        }
        for exp in seeker.experiences
    ]
    education = [
        {
            "degree": edu.degree,
            "field": edu.field_of_study,
            "school": edu.institution,
        }
        for edu in seeker.educations
    ]
    return {
        "id": seeker.id,
        "full_name": f"{seeker.first_name or ''} {seeker.last_name or ''}".strip(),
        "headline": seeker.about or "",
        "summary": seeker.about or "",
        "skills": skills,
        "experience": experience,
        "education": education,
    }


def _build_job_data(db: Session, job: Job) -> dict:
    """Build a data dict from a Job ORM object."""
    skills = [s.skill_name for s in job.skills]
    return {
        "id": job.id,
        "title": job.title,
        "description": job.description,
        "requirements": skills,
        "skills": skills,
        "experience_years": int(job.experience_years or 0),
        "education_level": job.education_level,
        "company_name": job.company.company_name if job.company else "",
    }


def _calc_years(start_date, end_date) -> int:
    """Calculate years between two dates."""
    if not start_date:
        return 0
    end = end_date or date.today()
    return max(0, (end - start_date).days // 365)


@router.get("/match/seeker/{seeker_id}/job/{job_id}")
async def get_match_score(
    seeker_id: UUID,
    job_id: UUID,
    db: Session = Depends(get_db),
    matching_service: MatchingService = Depends(get_matching_service),
    current_user: User = Depends(allow_seeker_only),
):
    """
    PB-12: Get match score between a specific seeker and job.
    """
    embedding_repo = EmbeddingRepository(db)
    company_repo = CompanyRepository(db)

    seeker = db.query(JobSeeker).filter(JobSeeker.id == seeker_id).first()
    if not seeker:
        raise HTTPException(status_code=404, detail="Seeker not found")
    if seeker.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized to view this seeker")

    job = company_repo.get_job_by_id(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    # Get or generate embeddings
    seeker_embedding = embedding_repo.get_by_seeker_id(seeker.id)
    job_embedding = embedding_repo.get_by_job_id(job.id)

    if not seeker_embedding:
        raise HTTPException(
            status_code=400,
            detail="Seeker embedding not found. Generate it first via POST /api/ai/embeddings/resume/{seeker_id}",
        )
    if not job_embedding:
        raise HTTPException(
            status_code=400,
            detail="Job embedding not found. Generate it first via POST /api/ai/embeddings/job/{job_id}",
        )

    seeker_data = _build_seeker_data(db, seeker)
    job_data = _build_job_data(db, job)

    result = matching_service.compute_match(
        seeker_data,
        job_data,
        seeker_embedding.embedding_vector,
        job_embedding.embedding_vector,
    )

    return {
        "seeker_id": seeker_id,
        "job_id": job_id,
        "match_percentage": result.match_percentage,
        "match_score": result.match_score,
        "breakdown": {
            "skills_match": result.breakdown.skills_match,
            "experience_match": result.breakdown.experience_match,
            "education_match": result.breakdown.education_match,
            "overall_text_match": result.breakdown.overall_text_match,
        },
        "matched_skills": result.matched_skills,
        "missing_skills": result.missing_skills,
    }


@router.get("/match/seeker/{seeker_id}/jobs")
async def get_seeker_job_matches(
    seeker_id: UUID,
    min_match: float = Query(0.0, ge=0, le=100),
    db: Session = Depends(get_db),
    matching_service: MatchingService = Depends(get_matching_service),
    current_user: User = Depends(allow_seeker_only),
):
    """
    PB-12: Get all jobs with match percentages for a seeker.
    """
    seeker = db.query(JobSeeker).filter(JobSeeker.id == seeker_id).first()
    if not seeker:
        raise HTTPException(status_code=404, detail="Seeker not found")
    if seeker.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized to view this seeker")

    embedding_repo = EmbeddingRepository(db)

    seeker_embedding = embedding_repo.get_by_seeker_id(seeker.id)
    if not seeker_embedding:
        raise HTTPException(
            status_code=400,
            detail="Seeker embedding not found. Generate it first.",
        )

    # Get all active jobs
    jobs = db.query(Job).filter(Job.status == JobStatus.ACTIVE).all()
    seeker_data = _build_seeker_data(db, seeker)

    results = []
    for job in jobs:
        job_embedding = embedding_repo.get_by_job_id(job.id)
        if not job_embedding:
            continue

        job_data = _build_job_data(db, job)
        match = matching_service.compute_match(
            seeker_data,
            job_data,
            seeker_embedding.embedding_vector,
            job_embedding.embedding_vector,
        )

        if match.match_percentage >= min_match:
            results.append({
                "job_id": job.id,
                "job_title": job.title,
                "company_name": job.company.company_name if job.company else "",
                "match_percentage": match.match_percentage,
                "match_score": match.match_score,
                "required_skills": job_data["skills"],
                "matched_skills": match.matched_skills,
                "missing_skills": match.missing_skills,
            })

    results.sort(key=lambda x: x["match_score"], reverse=True)

    return {
        "seeker_id": seeker_id,
        "min_match": min_match,
        "total_jobs": len(results),
        "jobs": results,
    }


@router.get("/match/job/{job_id}/candidates")
async def get_job_candidate_matches(
    job_id: UUID,
    min_score: float = Query(0.0, ge=0, le=100),
    db: Session = Depends(get_db),
    matching_service: MatchingService = Depends(get_matching_service),
    current_user: User = Depends(allow_company_only),
):
    """
    PB-17: Get all candidates ranked by match score for a job.
    """
    company_repo = CompanyRepository(db)
    embedding_repo = EmbeddingRepository(db)

    job = company_repo.get_job_by_id(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    if not job.company or job.company.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized to view candidates for this job")

    job_embedding = embedding_repo.get_by_job_id(job.id)
    if not job_embedding:
        raise HTTPException(
            status_code=400,
            detail="Job embedding not found. Generate it first.",
        )

    # Get all seekers with embeddings
    seekers = db.query(JobSeeker).all()
    job_data = _build_job_data(db, job)

    results = []
    for seeker in seekers:
        seeker_embedding = embedding_repo.get_by_seeker_id(seeker.id)
        if not seeker_embedding:
            continue

        seeker_data = _build_seeker_data(db, seeker)
        match = matching_service.compute_match(
            seeker_data,
            job_data,
            seeker_embedding.embedding_vector,
            job_embedding.embedding_vector,
        )

        if match.match_percentage >= min_score:
            results.append({
                "seeker_id": seeker.id,
                "full_name": f"{seeker.first_name or ''} {seeker.last_name or ''}".strip(),
                "email": seeker.user.email if seeker.user else "",
                "match_percentage": match.match_percentage,
                "match_score": match.match_score,
                "skills_match": match.breakdown.skills_match,
                "experience_match": match.breakdown.experience_match,
                "education_match": match.breakdown.education_match,
                "resume_url": seeker.resume_url,
            })

    results.sort(key=lambda x: x["match_score"], reverse=True)

    return {
        "job_id": job_id,
        "job_title": job.title,
        "total_candidates": len(results),
        "candidates": results,
    }


@router.post("/embeddings/resume/{seeker_id}")
async def generate_resume_embedding(
    seeker_id: UUID,
    db: Session = Depends(get_db),
    embedding_service: EmbeddingService = Depends(get_embedding_service),
    current_user: User = Depends(allow_seeker_only),
):
    """
    PB-15: Generate or update embedding for a seeker's resume.
    """
    embedding_repo = EmbeddingRepository(db)

    seeker = db.query(JobSeeker).filter(JobSeeker.id == seeker_id).first()
    if not seeker:
        raise HTTPException(status_code=404, detail="Seeker not found")
    if seeker.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized to update this seeker")

    seeker_data = _build_seeker_data(db, seeker)
    text = embedding_service.build_resume_text(seeker_data)
    vector = embedding_service.generate_embedding(text)

    embedding_repo.update("resume", seeker.id, vector, embedding_service.model_name)

    return {
        "seeker_id": seeker_id,
        "status": "success",
        "message": "Resume embedding generated successfully",
        "model": embedding_service.model_name,
        "dimension": len(vector),
    }


@router.post("/embeddings/job/{job_id}")
async def generate_job_embedding(
    job_id: UUID,
    db: Session = Depends(get_db),
    embedding_service: EmbeddingService = Depends(get_embedding_service),
    current_user: User = Depends(allow_company_only),
):
    """
    PB-15: Generate or update embedding for a job posting.
    """
    company_repo = CompanyRepository(db)
    embedding_repo = EmbeddingRepository(db)

    job = company_repo.get_job_by_id(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    if not job.company or job.company.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized to update this job")

    job_data = _build_job_data(db, job)
    text = embedding_service.build_job_text(job_data)
    vector = embedding_service.generate_embedding(text)

    embedding_repo.update("job", job.id, vector, embedding_service.model_name)

    return {
        "job_id": job_id,
        "status": "success",
        "message": "Job embedding generated successfully",
        "model": embedding_service.model_name,
        "dimension": len(vector),
    }


@router.get("/embeddings/status/{entity_type}/{entity_id}")
async def get_embedding_status(
    entity_type: str,
    entity_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Check if an embedding exists for a given entity."""
    if entity_type not in ("resume", "job"):
        raise HTTPException(status_code=400, detail="entity_type must be 'resume' or 'job'")

    if entity_type == "resume":
        seeker = db.query(JobSeeker).filter(JobSeeker.id == entity_id).first()
        if not seeker:
            raise HTTPException(status_code=404, detail="Seeker not found")
        if seeker.user_id != current_user.id or current_user.role != "job_seeker":
            raise HTTPException(status_code=403, detail="Not authorized to view this embedding")
    else:
        job = db.query(Job).filter(Job.id == entity_id).first()
        if not job:
            raise HTTPException(status_code=404, detail="Job not found")
        if not job.company or job.company.user_id != current_user.id or current_user.role != "company":
            raise HTTPException(status_code=403, detail="Not authorized to view this embedding")

    embedding_repo = EmbeddingRepository(db)
    exists = embedding_repo.exists(entity_type, entity_id)

    result = {
        "entity_type": entity_type,
        "entity_id": entity_id,
        "has_embedding": exists,
    }

    if exists:
        embedding = embedding_repo.get(entity_type, entity_id)
        result["model_version"] = embedding.model_version
        result["created_at"] = str(embedding.created_at)

    return result


@router.get("/model/info")
async def get_model_info(
    embedding_service: EmbeddingService = Depends(get_embedding_service),
):
    """Get information about the current embedding model."""
    return embedding_service.get_model_info()
