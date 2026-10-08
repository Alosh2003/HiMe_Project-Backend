"""
Embedding Repository
====================
Database operations for storing and retrieving vector embeddings.
"""

from sqlalchemy.orm import Session
from typing import Optional, List
from uuid import UUID

from app.models.embedding import Embedding


class EmbeddingRepository:
    def __init__(self, db: Session):
        self.db = db

    def get(self, entity_type: str, entity_id: UUID) -> Optional[Embedding]:
        """Get embedding by entity type and ID."""
        return (
            self.db.query(Embedding)
            .filter(
                Embedding.entity_type == entity_type,
                Embedding.entity_id == entity_id,
            )
            .first()
        )

    def get_by_seeker_id(self, seeker_id: UUID) -> Optional[Embedding]:
        """Get resume embedding by seeker ID."""
        return self.get("resume", seeker_id)

    def get_by_job_id(self, job_id: UUID) -> Optional[Embedding]:
        """Get job embedding by job ID."""
        return self.get("job", job_id)

    def create(
        self,
        entity_type: str,
        entity_id: UUID,
        embedding_vector: List[float],
        model_version: str = "all-MiniLM-L6-v2",
    ) -> Embedding:
        """Create a new embedding."""
        embedding = Embedding(
            entity_type=entity_type,
            entity_id=entity_id,
            embedding_vector=embedding_vector,
            model_version=model_version,
        )
        self.db.add(embedding)
        self.db.commit()
        self.db.refresh(embedding)
        return embedding

    def update(
        self,
        entity_type: str,
        entity_id: UUID,
        embedding_vector: List[float],
        model_version: str = "all-MiniLM-L6-v2",
    ) -> Optional[Embedding]:
        """Update existing embedding or create if not exists."""
        embedding = self.get(entity_type, entity_id)
        if embedding:
            embedding.embedding_vector = embedding_vector
            embedding.model_version = model_version
            self.db.commit()
            self.db.refresh(embedding)
            return embedding
        return self.create(entity_type, entity_id, embedding_vector, model_version)

    def delete(self, entity_type: str, entity_id: UUID) -> bool:
        """Delete an embedding."""
        embedding = self.get(entity_type, entity_id)
        if embedding:
            self.db.delete(embedding)
            self.db.commit()
            return True
        return False

    def get_all_resume_embeddings(self) -> List[Embedding]:
        """Get all resume embeddings."""
        return (
            self.db.query(Embedding)
            .filter(Embedding.entity_type == "resume")
            .all()
        )

    def get_all_job_embeddings(self) -> List[Embedding]:
        """Get all job embeddings."""
        return (
            self.db.query(Embedding)
            .filter(Embedding.entity_type == "job")
            .all()
        )

    def exists(self, entity_type: str, entity_id: UUID) -> bool:
        """Check if an embedding exists."""
        return (
            self.db.query(Embedding)
            .filter(
                Embedding.entity_type == entity_type,
                Embedding.entity_id == entity_id,
            )
            .count()
            > 0
        )
