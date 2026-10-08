"""
Matching Service
================
Computes match scores between candidates and jobs using embeddings.
"""

import logging
from typing import List, Optional, Dict, Any, Tuple
from dataclasses import dataclass, field
from uuid import UUID

from app.services.ai.embedding_service import EmbeddingService
from app.services.ai.text_preprocessor import TextPreprocessor

logger = logging.getLogger(__name__)


@dataclass
class MatchBreakdown:
    """Detailed breakdown of match score components."""
    skills_match: float = 0.0
    experience_match: float = 0.0
    education_match: float = 0.0
    overall_text_match: float = 0.0


@dataclass
class MatchResult:
    """Complete match result between a candidate and a job."""
    seeker_id: UUID
    job_id: UUID
    match_score: float
    match_percentage: float
    breakdown: MatchBreakdown
    matched_skills: List[str] = field(default_factory=list)
    missing_skills: List[str] = field(default_factory=list)
    seeker_name: str = ""
    job_title: str = ""
    company_name: str = ""


class MatchingService:
    """Service for computing candidate-job match scores."""

    # Weights for different components (should sum to 1.0)
    WEIGHT_SKILLS = 0.40
    WEIGHT_EXPERIENCE = 0.25
    WEIGHT_EDUCATION = 0.15
    WEIGHT_OVERALL = 0.20

    def __init__(self, embedding_service: EmbeddingService):
        self.embedding_service = embedding_service
        self.preprocessor = TextPreprocessor()

    def compute_match(
        self,
        seeker_data: Dict[str, Any],
        job_data: Dict[str, Any],
        seeker_embedding: List[float],
        job_embedding: List[float],
    ) -> MatchResult:
        """Compute comprehensive match score between candidate and job."""

        # Overall text similarity
        overall_sim = self.embedding_service.compute_similarity(
            seeker_embedding, job_embedding
        )

        # Component-level matching
        skills_match, matched, missing = self._compute_skills_match(
            seeker_data.get("skills", []),
            job_data.get("skills", []) or job_data.get("requirements", []),
        )

        experience_match = self._compute_experience_match(
            seeker_data.get("experience", []),
            int(job_data.get("experience_years") or 0),
        )

        education_match = self._compute_education_match(
            seeker_data.get("education", []),
            job_data.get("education_level", ""),
        )

        # Weighted final score
        final_score = (
            self.WEIGHT_SKILLS * skills_match
            + self.WEIGHT_EXPERIENCE * experience_match
            + self.WEIGHT_EDUCATION * education_match
            + self.WEIGHT_OVERALL * overall_sim
        )

        # Clamp to [0, 1]
        final_score = max(0.0, min(1.0, final_score))

        return MatchResult(
            seeker_id=seeker_data["id"],
            job_id=job_data["id"],
            match_score=round(final_score, 4),
            match_percentage=round(final_score * 100, 1),
            breakdown=MatchBreakdown(
                skills_match=round(skills_match, 4),
                experience_match=round(experience_match, 4),
                education_match=round(education_match, 4),
                overall_text_match=round(overall_sim, 4),
            ),
            matched_skills=matched,
            missing_skills=missing,
            seeker_name=seeker_data.get("full_name", ""),
            job_title=job_data.get("title", ""),
            company_name=job_data.get("company_name", ""),
        )

    def rank_candidates_for_job(
        self,
        job_data: Dict[str, Any],
        candidates: List[Dict[str, Any]],
        job_embedding: List[float],
        min_score: float = 0.0,
    ) -> List[MatchResult]:
        """Rank all candidates for a specific job by match score."""
        results = []

        for candidate in candidates:
            candidate_embedding = candidate.get("embedding", [])
            if not candidate_embedding:
                continue

            match = self.compute_match(
                candidate, job_data, candidate_embedding, job_embedding
            )

            if match.match_score >= min_score:
                results.append(match)

        # Sort descending by match score
        results.sort(key=lambda x: x.match_score, reverse=True)
        return results

    def rank_jobs_for_seeker(
        self,
        seeker_data: Dict[str, Any],
        jobs: List[Dict[str, Any]],
        seeker_embedding: List[float],
        min_score: float = 0.0,
    ) -> List[MatchResult]:
        """Rank all jobs for a specific seeker by match score."""
        results = []

        for job in jobs:
            job_embedding = job.get("embedding", [])
            if not job_embedding:
                continue

            match = self.compute_match(
                seeker_data, job, seeker_embedding, job_embedding
            )

            if match.match_score >= min_score:
                results.append(match)

        # Sort descending by match score
        results.sort(key=lambda x: x.match_score, reverse=True)
        return results

    def _compute_skills_match(
        self,
        candidate_skills: List[str],
        job_skills: List[str],
    ) -> Tuple[float, List[str], List[str]]:
        """Compute skills match using Jaccard-like similarity."""
        if not job_skills:
            return 1.0, candidate_skills, []

        candidate_set = set(self.preprocessor.normalize_skills(candidate_skills))
        job_set = set(self.preprocessor.normalize_skills(job_skills))

        if not job_set:
            return 1.0, list(candidate_set), []

        matched = candidate_set & job_set
        missing = job_set - candidate_set

        # Jaccard similarity: |A ∩ B| / |A ∪ B|
        union = candidate_set | job_set
        if not union:
            return 1.0, list(matched), []

        score = len(matched) / len(union)
        return score, list(matched), list(missing)

    def _compute_experience_match(
        self,
        candidate_experience: List[Dict],
        required_years: int,
    ) -> float:
        """Compare a job's minimum years with total seeker experience."""
        if required_years <= 0:
            return 1.0

        # Calculate total years of experience
        total_years = 0
        for exp in candidate_experience:
            years = exp.get("years", 0)
            if isinstance(years, (int, float)):
                total_years += years

        if total_years >= required_years:
            return 1.0
        else:
            return total_years / required_years

    @staticmethod
    def _normalize_education_level(value: str) -> Optional[str]:
        normalized = value.casefold().strip().replace(" ", "_")
        aliases = {
            "high_school": "high_school",
            "secondary": "high_school",
            "ثانوية": "high_school",
            "diploma": "diploma",
            "دبلوم": "diploma",
            "bachelor": "bachelor",
            "بكالوريوس": "bachelor",
            "master": "master",
            "ماجستير": "master",
            "phd": "phd",
            "doctorate": "phd",
            "دكتوراه": "phd",
        }
        for alias, level in aliases.items():
            if alias in normalized:
                return level
        return None

    def _compute_education_match(
        self,
        candidate_education: List[Dict],
        required_level: str,
    ) -> float:
        """Compute education level match."""
        if not required_level:
            return 1.0

        # Education level hierarchy
        edu_levels = {
            "high_school": 1,
            "diploma": 2,
            "bachelor": 3,
            "master": 4,
            "phd": 5,
        }

        normalized_required = self._normalize_education_level(required_level)
        required = edu_levels.get(normalized_required or "", 0)
        if not required:
            return 1.0

        # Get candidate's highest education level
        candidate_max = 0
        for edu in candidate_education:
            degree = self._normalize_education_level(edu.get("degree", ""))
            candidate_max = max(candidate_max, edu_levels.get(degree or "", 0))

        if candidate_max >= required:
            return 1.0
        else:
            return candidate_max / required
