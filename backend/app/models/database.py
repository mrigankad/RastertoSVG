"""Database models for Phase 9: User Accounts & Cloud Platform.

SQLAlchemy ORM models for:
- User accounts (email + OAuth)
- Team workspaces
- Projects & conversions
- API keys
- Usage tracking
"""

import uuid
from datetime import datetime, timezone
from enum import Enum
from typing import Optional

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Enum as SAEnum,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    BigInteger,
    Index,
    UniqueConstraint,
    JSON,
)
from sqlalchemy.orm import DeclarativeBase, relationship


class Base(DeclarativeBase):
    """Base class for all ORM models."""

    pass


# =============================================================================
# Enums
# =============================================================================


class UserRole(str, Enum):
    USER = "user"
    TEAM_ADMIN = "team_admin"
    ENTERPRISE_ADMIN = "enterprise_admin"
    SUPERADMIN = "superadmin"


class PlanTier(str, Enum):
    FREE = "free"
    PRO = "pro"
    TEAM = "team"
    ENTERPRISE = "enterprise"


class OAuthProvider(str, Enum):
    GOOGLE = "google"
    GITHUB = "github"
    MICROSOFT = "microsoft"


class ProjectStatus(str, Enum):
    ACTIVE = "active"
    ARCHIVED = "archived"
    DELETED = "deleted"


class ConversionStatus(str, Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


# =============================================================================
# User & Auth Models
# =============================================================================


class User(Base):
    __tablename__ = "users"
    __table_args__ = (Index("ix_users_email", "email", unique=True),)

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    email = Column(String(255), nullable=False, unique=True)
    username = Column(String(100), nullable=True, unique=True)
    display_name = Column(String(255), nullable=True)
    hashed_password = Column(String(255), nullable=True)  # Null for OAuth-only users
    avatar_url = Column(String(512), nullable=True)

    # Account state
    is_active = Column(Boolean, default=True)
    is_verified = Column(Boolean, default=False)
    role = Column(SAEnum(UserRole), default=UserRole.USER)
    plan = Column(SAEnum(PlanTier), default=PlanTier.FREE)

    # Verification & reset tokens
    verification_token = Column(String(255), nullable=True)
    reset_token = Column(String(255), nullable=True)
    reset_token_expires = Column(DateTime(timezone=True), nullable=True)

    # Timestamps
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )
    last_login_at = Column(DateTime(timezone=True), nullable=True)

    # Preferences (JSON)
    preferences = Column(JSON, default=dict)

    # Relationships
    oauth_accounts = relationship(
        "OAuthAccount", back_populates="user", cascade="all, delete-orphan"
    )
    api_keys = relationship("APIKey", back_populates="user", cascade="all, delete-orphan")
    projects = relationship("Project", back_populates="owner", cascade="all, delete-orphan")
    conversions = relationship("Conversion", back_populates="user", cascade="all, delete-orphan")
    presets = relationship("UserPreset", back_populates="user", cascade="all, delete-orphan")
    team_memberships = relationship(
        "TeamMember", back_populates="user", cascade="all, delete-orphan"
    )
    usage_records = relationship("UsageRecord", back_populates="user", cascade="all, delete-orphan")


class OAuthAccount(Base):
    __tablename__ = "oauth_accounts"
    __table_args__ = (
        UniqueConstraint("provider", "provider_user_id", name="uq_oauth_provider_user"),
    )

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    provider = Column(SAEnum(OAuthProvider), nullable=False)
    provider_user_id = Column(String(255), nullable=False)
    provider_email = Column(String(255), nullable=True)
    access_token = Column(Text, nullable=True)
    refresh_token = Column(Text, nullable=True)
    token_expires_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    user = relationship("User", back_populates="oauth_accounts")


class APIKey(Base):
    __tablename__ = "api_keys"
    __table_args__ = (Index("ix_api_keys_key_hash", "key_hash", unique=True),)

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    team_id = Column(String(36), ForeignKey("teams.id", ondelete="SET NULL"), nullable=True)
    name = Column(String(255), nullable=False)
    key_prefix = Column(String(8), nullable=False)  # First 8 chars for identification
    key_hash = Column(String(255), nullable=False)  # SHA-256 hash of the full key
    scopes = Column(JSON, default=list)  # ["convert", "upload", "analyze", "admin"]
    is_active = Column(Boolean, default=True)
    last_used_at = Column(DateTime(timezone=True), nullable=True)
    expires_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    user = relationship("User", back_populates="api_keys")
    team = relationship("Team", back_populates="api_keys")


# =============================================================================
# Team & Collaboration Models
# =============================================================================


class Team(Base):
    __tablename__ = "teams"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    name = Column(String(255), nullable=False)
    slug = Column(String(100), nullable=False, unique=True)
    description = Column(Text, nullable=True)
    avatar_url = Column(String(512), nullable=True)
    plan = Column(SAEnum(PlanTier), default=PlanTier.TEAM)
    max_members = Column(Integer, default=10)
    storage_quota_mb = Column(Integer, default=10240)  # 10GB default
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    # Relationships
    members = relationship("TeamMember", back_populates="team", cascade="all, delete-orphan")
    projects = relationship("Project", back_populates="team")
    api_keys = relationship("APIKey", back_populates="team")


class TeamMember(Base):
    __tablename__ = "team_members"
    __table_args__ = (UniqueConstraint("team_id", "user_id", name="uq_team_member"),)

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    team_id = Column(String(36), ForeignKey("teams.id", ondelete="CASCADE"), nullable=False)
    user_id = Column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    role = Column(SAEnum(UserRole), default=UserRole.USER)
    joined_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    team = relationship("Team", back_populates="members")
    user = relationship("User", back_populates="team_memberships")


# =============================================================================
# Project & Conversion Models
# =============================================================================


class Project(Base):
    __tablename__ = "projects"
    __table_args__ = (
        Index("ix_projects_owner", "owner_id"),
        Index("ix_projects_team", "team_id"),
    )

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    owner_id = Column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    team_id = Column(String(36), ForeignKey("teams.id", ondelete="SET NULL"), nullable=True)
    name = Column(String(255), nullable=False, default="Untitled Project")
    description = Column(Text, nullable=True)
    status = Column(SAEnum(ProjectStatus), default=ProjectStatus.ACTIVE)
    is_starred = Column(Boolean, default=False)
    tags = Column(JSON, default=list)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    owner = relationship("User", back_populates="projects")
    team = relationship("Team", back_populates="projects")
    conversions = relationship("Conversion", back_populates="project", cascade="all, delete-orphan")


class Conversion(Base):
    __tablename__ = "conversions"
    __table_args__ = (
        Index("ix_conversions_user", "user_id"),
        Index("ix_conversions_project", "project_id"),
        Index("ix_conversions_created", "created_at"),
    )

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    project_id = Column(String(36), ForeignKey("projects.id", ondelete="SET NULL"), nullable=True)

    # Input
    original_filename = Column(String(255), nullable=False)
    original_format = Column(String(20), nullable=True)
    original_size_bytes = Column(BigInteger, nullable=True)
    original_width = Column(Integer, nullable=True)
    original_height = Column(Integer, nullable=True)
    input_storage_key = Column(String(512), nullable=True)  # S3 key

    # Output
    output_storage_key = Column(String(512), nullable=True)  # S3 key
    output_size_bytes = Column(BigInteger, nullable=True)
    output_format = Column(String(20), default="svg")

    # Processing
    status = Column(SAEnum(ConversionStatus), default=ConversionStatus.PENDING)
    engine_used = Column(String(50), nullable=True)
    quality_mode = Column(String(50), nullable=True)
    processing_route = Column(String(20), nullable=True)  # "wasm", "server", "hybrid"
    processing_time_ms = Column(Integer, nullable=True)
    ai_features_used = Column(JSON, default=list)
    parameters = Column(JSON, default=dict)
    error_message = Column(Text, nullable=True)

    # Metadata
    is_starred = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    completed_at = Column(DateTime(timezone=True), nullable=True)

    user = relationship("User", back_populates="conversions")
    project = relationship("Project", back_populates="conversions")


# =============================================================================
# Presets & Settings
# =============================================================================


class UserPreset(Base):
    __tablename__ = "user_presets"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    team_id = Column(String(36), ForeignKey("teams.id", ondelete="SET NULL"), nullable=True)
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    is_public = Column(Boolean, default=False)
    is_default = Column(Boolean, default=False)

    # Preset configuration
    config = Column(JSON, nullable=False, default=dict)
    # config = {
    #   "engine": "vtracer",
    #   "quality_mode": "standard",
    #   "preprocessing": { "denoise": true, ... },
    #   "ai_mode": "balanced",
    #   ...
    # }

    use_count = Column(Integer, default=0)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    user = relationship("User", back_populates="presets")


# =============================================================================
# Usage & Billing
# =============================================================================


class UsageRecord(Base):
    __tablename__ = "usage_records"
    __table_args__ = (Index("ix_usage_user_period", "user_id", "period_start"),)

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    period_start = Column(DateTime(timezone=True), nullable=False)
    period_end = Column(DateTime(timezone=True), nullable=False)

    # Counters
    conversions_count = Column(Integer, default=0)
    api_calls_count = Column(Integer, default=0)
    storage_used_bytes = Column(BigInteger, default=0)
    compute_seconds = Column(Float, default=0.0)
    bandwidth_bytes = Column(BigInteger, default=0)

    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    user = relationship("User", back_populates="usage_records")


# =============================================================================
# Plan limits
# =============================================================================

PLAN_LIMITS = {
    PlanTier.FREE: {
        "conversions_per_month": 25,
        "storage_mb": 500,
        "max_file_size_mb": 10,
        "api_calls_per_day": 100,
        "max_image_dimension": 4096,
        "ai_modes": ["auto", "speed", "balanced"],
        "export_formats": ["svg"],
        "team_size": 0,
        "batch_limit": 5,
        "priority": "low",
    },
    PlanTier.PRO: {
        "conversions_per_month": -1,  # Unlimited
        "storage_mb": 10240,
        "max_file_size_mb": 50,
        "api_calls_per_day": 10000,
        "max_image_dimension": 16384,
        "ai_modes": ["auto", "speed", "balanced", "quality", "max_quality"],
        "export_formats": ["svg", "pdf", "eps", "dxf"],
        "team_size": 0,
        "batch_limit": 50,
        "priority": "normal",
    },
    PlanTier.TEAM: {
        "conversions_per_month": -1,
        "storage_mb": 51200,
        "max_file_size_mb": 100,
        "api_calls_per_day": 50000,
        "max_image_dimension": 16384,
        "ai_modes": ["auto", "speed", "balanced", "quality", "max_quality"],
        "export_formats": ["svg", "pdf", "eps", "dxf", "emf"],
        "team_size": 10,
        "batch_limit": 200,
        "priority": "high",
    },
    PlanTier.ENTERPRISE: {
        "conversions_per_month": -1,
        "storage_mb": -1,  # Unlimited
        "max_file_size_mb": 200,
        "api_calls_per_day": -1,
        "max_image_dimension": 32768,
        "ai_modes": ["auto", "speed", "balanced", "quality", "max_quality"],
        "export_formats": ["svg", "pdf", "eps", "dxf", "emf", "wmf"],
        "team_size": -1,
        "batch_limit": -1,
        "priority": "critical",
    },
}
