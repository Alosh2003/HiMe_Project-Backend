from datetime import datetime, timezone
import uuid
import enum
from sqlalchemy import Column, DateTime, Integer, String, ForeignKey, UniqueConstraint, Enum, Boolean, UUID
from sqlalchemy.orm import relationship
from app.db.base import Base

class UserRole(str, enum.Enum):
    COMPANY = "company"
    JOB_SEEKER = "job_seeker"

class User(Base):
    __tablename__ = "users"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email = Column(String, unique=True, index=True, nullable=False)
    password_hash = Column(String, nullable=True)
    
    role = Column(
        Enum(UserRole, name="user_role_enum", values_callable=lambda obj: [e.value for e in obj]),
        default=UserRole.JOB_SEEKER.value,
        nullable=False
    )
    is_verified = Column(Boolean, default=False, nullable=False)
    blocked_until = Column(DateTime(timezone=True), nullable=True)

    # 1. الحسابات الاجتماعية
    oauth_accounts = relationship(
        "OAuthAccount",
        back_populates="user",
        cascade="all, delete-orphan"
    )

    # 2. بروفايل الباحث عن عمل
    seeker_profile = relationship(
        "JobSeeker",
        back_populates="user",
        cascade="all, delete-orphan",
        uselist=False
    )

    # 3. بروفايل الشركة (الحل الجذري للخطأ)
    company_profile = relationship(
        "Company",
        back_populates="user",
        cascade="all, delete-orphan",
        uselist=False
    )


class OAuthProvider(str, enum.Enum):
    GOOGLE = "google"
    FACEBOOK = "facebook"
    LINKEDIN = "linkedin"

class OAuthAccount(Base):
    __tablename__ = "oauth_accounts"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    
    provider = Column(
        Enum(OAuthProvider, name="oauth_provider_enum", values_callable=lambda obj: [e.value for e in obj]),
        nullable=False
    )
    
    provider_account_id = Column(String, nullable=False)
    user = relationship("User", back_populates="oauth_accounts")

    __table_args__ = (
        UniqueConstraint("provider", "provider_account_id", name="uq_provider_account"),
    )

class TokenType(str, enum.Enum):
    EMAIL_VERIFY = "email_verify"
    PASSWORD_RESET = "password_reset"
    TWO_FACTOR = "two_factor"

class VerificationCode(Base):
    __tablename__ = "verification_codes"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    code_hash = Column(String, nullable=False)
    token_type = Column(Enum(TokenType, name="token_type_enum"), nullable=False)
    target = Column(String, nullable=True)
    expires_at = Column(DateTime(timezone=True), nullable=False)
    attempts = Column(Integer, default=0, nullable=False)
    is_used = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)

class IPRateLimit(Base):
    __tablename__ = "ip_rate_limits"

    ip_address = Column(String, primary_key=True, index=True)
    action = Column(String, primary_key=True)
    request_count = Column(Integer, default=1, nullable=False)
    first_request_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)