"""
Embedding Model
===============
SQLAlchemy model for storing vector embeddings.
"""

from sqlalchemy import (
    Column,
    Integer,
    String,
    Float,
    DateTime,
    UniqueConstraint,
    Index,
    UUID,
    JSON,
)
from datetime import datetime

from app.db.base import Base


class Embedding(Base):
    """Stores vector embeddings for resumes and jobs."""

    __tablename__ = "embeddings"

    id = Column(Integer, primary_key=True, index=True)
    entity_type = Column(String(20), nullable=False)  # 'resume' or 'job'
    entity_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    embedding_vector = Column(JSON, nullable=False)  # 384-dim vector
    model_version = Column(String(50), nullable=False, default="all-MiniLM-L6-v2")
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    __table_args__ = (
        UniqueConstraint("entity_type", "entity_id", name="uq_entity_type_id"),
        Index("ix_embeddings_entity", "entity_type", "entity_id"),
        Index("ix_embeddings_model", "model_version"),
    )

    def __repr__(self):
        return f"<Embedding({self.entity_type}:{self.entity_id}, model={self.model_version})>"
