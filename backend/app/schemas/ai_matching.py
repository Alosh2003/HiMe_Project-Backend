"""
AI Matching Schemas
===================
Pydantic models for AI matching API request/response validation.
"""

from pydantic import BaseModel, Field
from typing import List, Optional
from uuid import UUID


class MatchBreakdownSchema(BaseModel):
    """Detailed breakdown of match score components."""
    skills_match: float = Field(0.0, ge=0, le=1)
    experience_match: float = Field(0.0, ge=0, le=1)
    education_match: float = Field(0.0, ge=0, le=1)
    overall_text_match: float = Field(0.0, ge=0, le=1)


class MatchScoreResponse(BaseModel):
    """Response for a single match score query."""
    seeker_id: UUID
    job_id: UUID
    match_percentage: float = Field(0.0, ge=0, le=100)
    match_score: float = Field(0.0, ge=0, le=1)
    breakdown: MatchBreakdownSchema
    matched_skills: List[str] = []
    missing_skills: List[str] = []


class JobMatchResult(BaseModel):
    """Match result for a job seeker viewing a job."""
    job_id: UUID
    job_title: str
    company_name: str
    match_percentage: float
    match_score: float
    required_skills: List[str] = []
    matched_skills: List[str] = []
    missing_skills: List[str] = []


class SeekerJobsMatchesResponse(BaseModel):
    """Response for seeker viewing all job matches."""
    seeker_id: UUID
    total_jobs: int
    jobs: List[JobMatchResult]


class CandidateMatchResult(BaseModel):
    """Match result for an employer viewing a candidate."""
    seeker_id: UUID
    full_name: str
    email: str
    match_percentage: float
    match_score: float
    skills_match: Optional[float] = None
    experience_match: Optional[float] = None
    education_match: Optional[float] = None
    resume_url: Optional[str] = None


class JobCandidatesMatchesResponse(BaseModel):
    """Response for employer viewing ranked candidates."""
    job_id: UUID
    job_title: str
    total_candidates: int
    candidates: List[CandidateMatchResult]


class EmbeddingStatusResponse(BaseModel):
    """Response for embedding status check."""
    entity_type: str
    entity_id: UUID
    has_embedding: bool
    model_version: Optional[str] = None
    created_at: Optional[str] = None


class EmbeddingGenerationResponse(BaseModel):
    """Response for embedding generation request."""
    entity_type: str
    entity_id: UUID
    status: str
    message: str


class ModelInfoResponse(BaseModel):
    """Response for model information."""
    model_name: str
    embedding_dimension: int
    loaded: bool
