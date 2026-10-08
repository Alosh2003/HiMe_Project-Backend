"""
Embedding Service
=================
Generates and manages vector embeddings for resumes and jobs.
Includes safe fallback for lightweight cloud serverless environments (e.g. Vercel).
"""

import logging
import math
from typing import List, Optional, Dict, Any
from datetime import datetime

from app.services.ai.text_preprocessor import TextPreprocessor

logger = logging.getLogger(__name__)

try:
    import numpy as np
except (ImportError, ModuleNotFoundError):
    np = None
    logger.warning("NumPy is not available. Using the standard-library similarity fallback.")

# استيراد آمن لتفادي انهيار السيرفر في البيئات السحابية الخفيفة
try:
    from sentence_transformers import SentenceTransformer
    HAS_TRANSFORMERS = True
except (ImportError, ModuleNotFoundError):
    SentenceTransformer = None
    HAS_TRANSFORMERS = False
    logger.warning("sentence-transformers is not available. Operating in safe fallback mode.")


class EmbeddingService:
    """Service for generating and managing text embeddings."""

    DEFAULT_MODEL = "all-MiniLM-L6-v2"
    EMBEDDING_DIMENSION = 384

    def __init__(self, model_name: str = None):
        self.model_name = model_name or self.DEFAULT_MODEL
        self._model = None
        self.preprocessor = TextPreprocessor()

    @property
    def model(self):
        """Lazy-load the embedding model if available."""
        if not HAS_TRANSFORMERS:
            return None

        if self._model is None:
            try:
                logger.info(f"Loading embedding model: {self.model_name}")
                self._model = SentenceTransformer(self.model_name)
                logger.info("Embedding model loaded successfully")
            except Exception as e:
                logger.error(f"Failed to load embedding model: {e}")
                self._model = None
        return self._model

    def generate_embedding(self, text: str) -> List[float]:
        """Generate embedding vector or return fallback vector."""
        if not text or not text.strip():
            return [0.0] * self.EMBEDDING_DIMENSION

        if self.model is not None:
            cleaned_text = self.preprocessor.clean(text)
            embedding = self.model.encode(cleaned_text, normalize_embeddings=True)
            return embedding.tolist()

        # Fallback: متجه صفري بطول 384 لمنع أخطاء الإدخال في قاعدة البيانات
        return [0.0] * self.EMBEDDING_DIMENSION

    def generate_embeddings_batch(self, texts: List[str]) -> List[List[float]]:
        """Generate embeddings for multiple texts."""
        if not texts:
            return []

        if self.model is not None:
            cleaned_texts = [self.preprocessor.clean(t) for t in texts]
            embeddings = self.model.encode(
                cleaned_texts,
                batch_size=32,
                show_progress_bar=False,
                normalize_embeddings=True,
            )
            return embeddings.tolist()

        return [[0.0] * self.EMBEDDING_DIMENSION for _ in texts]

    def build_resume_text(self, seeker_data: Dict[str, Any]) -> str:
        """Build a text representation from structured resume data."""
        parts = []

        if seeker_data.get("headline"):
            parts.append(seeker_data["headline"])

        if seeker_data.get("summary"):
            parts.append(seeker_data["summary"])

        skills = seeker_data.get("skills", [])
        if skills:
            parts.append("Skills: " + ", ".join(skills))

        experience = seeker_data.get("experience", [])
        if experience:
            exp_texts = []
            for exp in experience:
                role = exp.get("title", "")
                company = exp.get("company", "")
                desc = exp.get("description", "")
                exp_texts.append(f"{role} at {company}: {desc}")
            parts.append("Experience: " + " | ".join(exp_texts))

        education = seeker_data.get("education", [])
        if education:
            edu_texts = []
            for edu in education:
                degree = edu.get("degree", "")
                field = edu.get("field", "")
                school = edu.get("school", "")
                edu_texts.append(f"{degree} in {field} from {school}")
            parts.append("Education: " + " | ".join(edu_texts))

        return " ".join(parts)

    def build_job_text(self, job_data: Dict[str, Any]) -> str:
        """Build a text representation from structured job data."""
        parts = []

        if job_data.get("title"):
            parts.append(job_data["title"])

        if job_data.get("description"):
            parts.append(job_data["description"])

        requirements = job_data.get("requirements", [])
        if requirements:
            parts.append("Requirements: " + ", ".join(requirements))

        skills = job_data.get("skills", [])
        if skills:
            parts.append("Skills: " + ", ".join(skills))

        if job_data.get("experience_years"):
            parts.append(
                f"Minimum experience: {int(job_data['experience_years'])} years"
            )
        elif job_data.get("experience_level"):
            parts.append(f"Experience level: {job_data['experience_level']}")

        if job_data.get("education_level"):
            parts.append(f"Education level: {job_data['education_level']}")

        return " ".join(parts)

    def compute_similarity(self, embedding_a: List[float], embedding_b: List[float]) -> float:
        """Compute cosine similarity between two embeddings."""
        if np is None:
            if len(embedding_a) != len(embedding_b):
                raise ValueError("Embeddings must have the same dimensions")

            dot_product = sum(
                float(value_a) * float(value_b)
                for value_a, value_b in zip(embedding_a, embedding_b)
            )
            norm_a = math.sqrt(sum(float(value) ** 2 for value in embedding_a))
            norm_b = math.sqrt(sum(float(value) ** 2 for value in embedding_b))

            if norm_a == 0 or norm_b == 0:
                return 0.0

            return float(dot_product / (norm_a * norm_b))

        a = np.array(embedding_a)
        b = np.array(embedding_b)

        dot_product = np.dot(a, b)
        norm_a = np.linalg.norm(a)
        norm_b = np.linalg.norm(b)

        if norm_a == 0 or norm_b == 0:
            return 0.0

        return float(dot_product / (norm_a * norm_b))

    def get_model_info(self) -> Dict[str, Any]:
        """Return information about the embedding model."""
        return {
            "model_name": self.model_name,
            "embedding_dimension": self.EMBEDDING_DIMENSION,
            "loaded": self._model is not None,
        }