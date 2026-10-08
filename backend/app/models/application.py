import uuid
from datetime import datetime
from sqlalchemy import Column, String, DateTime, ForeignKey, UniqueConstraint, UUID
from sqlalchemy.orm import relationship

from app.db.base import Base


class JobApplication(Base):
    __tablename__ = "job_applications"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    job_id = Column(
        UUID(as_uuid=True),
        ForeignKey("jobs.id", ondelete="CASCADE"),
        nullable=False,
    )
    seeker_id = Column(
        UUID(as_uuid=True),
        ForeignKey("job_seekers.id", ondelete="CASCADE"),
        nullable=False,
    )
    # الحالات المعتمدة: pending, reviewed, contact, hired, rejected
    status = Column(String(20), default="pending", nullable=False)
    applied_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    # قيد لمنع تقديم الباحث على نفس الوظيفة مرتين نهائياً
    __table_args__ = (
        UniqueConstraint("job_id", "seeker_id", name="uq_job_seeker_application"),
    )

    # العلاقات
    job = relationship("Job", backref="applications")
    seeker = relationship("JobSeeker", backref="applications")