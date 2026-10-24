"""Canonical SQLAlchemy domain models for Memoryhive."""

import enum
import uuid
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import (
    JSON,
    Boolean,
    CheckConstraint,
    Column,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Table,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


def new_uuid() -> str:
    return str(uuid.uuid4())


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class ItemType(str, enum.Enum):
    LINK = "link"
    SCREENSHOT = "screenshot"
    TEXT = "text"
    DOCUMENT = "document"


class ProcessingStatus(str, enum.Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    READY = "ready"
    FAILED = "failed"
    SKIPPED = "skipped"


class AnalysisStatus(str, enum.Enum):
    NOT_ANALYZED = "not_analyzed"
    PENDING = "pending"
    SCHEDULED = "scheduled"
    ANALYZING = "analyzing"
    ANALYZED = "analyzed"
    DEGRADED = "degraded"
    FAILED = "failed"
    SKIPPED = "skipped"


class AnalysisExecutionBackend(str, enum.Enum):
    DATABASE = "database"
    TEMPORAL = "temporal"


class UserRole(str, enum.Enum):
    ADMIN = "admin"
    USER = "user"


item_tags = Table(
    "item_tags",
    Base.metadata,
    Column(
        "item_id",
        String(36),
        ForeignKey("items.id", ondelete="CASCADE"),
        primary_key=True,
    ),
    Column(
        "tag_id",
        String(36),
        ForeignKey("tags.id", ondelete="CASCADE"),
        primary_key=True,
    ),
)


class User(Base):
    __tablename__ = "users"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    hashed_password: Mapped[str] = mapped_column(String(255))
    name: Mapped[str | None] = mapped_column(String(255))
    role: Mapped[str] = mapped_column(
        String(20), default=UserRole.USER.value, server_default=UserRole.USER.value
    )
    session_version: Mapped[int] = mapped_column(Integer, default=1, server_default="1")
    password_changed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True)
    )
    is_active: Mapped[bool] = mapped_column(
        Boolean, default=True, server_default="true"
    )
    ai_external_processing_allowed: Mapped[bool] = mapped_column(
        Boolean, default=False, server_default="false"
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utc_now,
        server_default=func.now(),
        onupdate=utc_now,
    )

    items: Mapped[list["Item"]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )
    categories: Mapped[list["Category"]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )
    tags: Mapped[list["Tag"]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )
    refresh_tokens: Mapped[list["RefreshToken"]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )


class Category(Base):
    __tablename__ = "categories"
    __table_args__ = (
        UniqueConstraint("user_id", "name", name="uq_categories_user_name"),
        Index("ix_categories_user_id", "user_id"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    user_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="CASCADE")
    )
    name: Mapped[str] = mapped_column(String(100))
    color: Mapped[str] = mapped_column(String(20), default="#3b82f6")
    icon: Mapped[str] = mapped_column(String(50), default="folder")
    description: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utc_now,
        server_default=func.now(),
        onupdate=utc_now,
    )

    user: Mapped["User"] = relationship(back_populates="categories")
    items: Mapped[list["Item"]] = relationship(back_populates="category")


class Tag(Base):
    __tablename__ = "tags"
    __table_args__ = (
        UniqueConstraint("user_id", "name", name="uq_tags_user_name"),
        Index("ix_tags_user_id", "user_id"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    user_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="CASCADE")
    )
    name: Mapped[str] = mapped_column(String(50))
    color: Mapped[str] = mapped_column(String(20), default="#6b7280")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utc_now,
        server_default=func.now(),
        onupdate=utc_now,
    )

    user: Mapped["User"] = relationship(back_populates="tags")
    items: Mapped[list["Item"]] = relationship(
        secondary=item_tags, back_populates="tags"
    )


class Item(Base):
    __tablename__ = "items"
    __table_args__ = (
        CheckConstraint(
            "(type != 'link' OR url IS NOT NULL) AND "
            "(type != 'text' OR raw_text IS NOT NULL)",
            name="ck_items_required_content",
        ),
        CheckConstraint("revision > 0", name="ck_items_revision_positive"),
        Index("ix_items_user_created", "user_id", "created_at"),
        Index("ix_items_user_updated", "user_id", "updated_at"),
        Index("ix_items_user_type", "user_id", "type"),
        Index("ix_items_category_id", "category_id"),
        Index("ix_items_deleted_at", "deleted_at"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    user_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="CASCADE")
    )
    type: Mapped[ItemType] = mapped_column(String(20))
    url: Mapped[str | None] = mapped_column(Text)
    normalized_url: Mapped[str | None] = mapped_column(Text)
    raw_text: Mapped[str | None] = mapped_column(Text)
    title: Mapped[str | None] = mapped_column(String(500))
    description: Mapped[str | None] = mapped_column(Text)
    notes: Mapped[str | None] = mapped_column(Text)
    source: Mapped[str | None] = mapped_column(String(100))
    source_domain: Mapped[str | None] = mapped_column(String(255))
    author: Mapped[str | None] = mapped_column(String(255))
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    favicon_url: Mapped[str | None] = mapped_column(Text)
    extracted_text: Mapped[str | None] = mapped_column(Text)
    normalized_text: Mapped[str | None] = mapped_column(Text)
    language: Mapped[str | None] = mapped_column(String(20))
    summary: Mapped[str | None] = mapped_column(Text)
    item_metadata: Mapped[dict[str, Any] | None] = mapped_column("metadata", JSON)
    processing_status: Mapped[ProcessingStatus] = mapped_column(
        String(20), default=ProcessingStatus.PENDING, server_default="pending"
    )
    processing_error: Mapped[str | None] = mapped_column(Text)
    analysis_status: Mapped[AnalysisStatus] = mapped_column(
        String(20), default=AnalysisStatus.PENDING, server_default="pending"
    )
    analysis_error: Mapped[str | None] = mapped_column(Text)
    analysis_version: Mapped[int] = mapped_column(
        Integer, default=1, server_default="1"
    )
    analysis_requested_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True)
    )
    analysis_started_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True)
    )
    analysis_completed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True)
    )
    category_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("categories.id", ondelete="SET NULL")
    )
    is_favorite: Mapped[bool] = mapped_column(
        Boolean, default=False, server_default="false"
    )
    is_archived: Mapped[bool] = mapped_column(
        Boolean, default=False, server_default="false"
    )
    read_count: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    last_visited_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    revision: Mapped[int] = mapped_column(Integer, default=1, server_default="1")
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utc_now,
        server_default=func.now(),
        onupdate=utc_now,
    )

    user: Mapped["User"] = relationship(back_populates="items")
    category: Mapped["Category | None"] = relationship(back_populates="items")
    tags: Mapped[list["Tag"]] = relationship(
        secondary=item_tags, back_populates="items", lazy="selectin"
    )
    assets: Mapped[list["Asset"]] = relationship(
        back_populates="item", cascade="all, delete-orphan", lazy="selectin"
    )
    processing_jobs: Mapped[list["ProcessingJob"]] = relationship(
        back_populates="item", cascade="all, delete-orphan"
    )


class Asset(Base):
    __tablename__ = "assets"
    __table_args__ = (
        CheckConstraint("size_bytes >= 0", name="ck_assets_size_nonnegative"),
        UniqueConstraint("object_key", name="uq_assets_object_key"),
        Index("ix_assets_item_id", "item_id"),
        Index("ix_assets_user_id", "user_id"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    item_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("items.id", ondelete="CASCADE")
    )
    user_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="CASCADE")
    )
    object_key: Mapped[str] = mapped_column(Text)
    original_filename: Mapped[str | None] = mapped_column(String(255))
    mime_type: Mapped[str] = mapped_column(String(100))
    size_bytes: Mapped[int] = mapped_column(Integer)
    sha256: Mapped[str | None] = mapped_column(String(64))
    width: Mapped[int | None] = mapped_column(Integer)
    height: Mapped[int | None] = mapped_column(Integer)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, server_default=func.now()
    )

    item: Mapped["Item"] = relationship(back_populates="assets")


class RefreshToken(Base):
    __tablename__ = "refresh_tokens"
    __table_args__ = (
        UniqueConstraint("token_hash", name="uq_refresh_tokens_hash"),
        Index("ix_refresh_tokens_user_id", "user_id"),
        Index("ix_refresh_tokens_expires_at", "expires_at"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    user_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="CASCADE")
    )
    token_hash: Mapped[str] = mapped_column(String(64))
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, server_default=func.now()
    )

    user: Mapped["User"] = relationship(back_populates="refresh_tokens")


class LifecycleAudit(Base):
    __tablename__ = "lifecycle_audits"
    __table_args__ = (Index("ix_lifecycle_audits_user_id", "user_id"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    user_id: Mapped[str] = mapped_column(String(36))
    event: Mapped[str] = mapped_column(String(50))
    status: Mapped[str] = mapped_column(String(20), default="pending")
    object_count: Mapped[int] = mapped_column(Integer, default=0)
    error_count: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, server_default=func.now()
    )
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class StorageDeletionJob(Base):
    __tablename__ = "storage_deletion_jobs"
    __table_args__ = (Index("ix_storage_deletion_jobs_audit_id", "audit_id"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    audit_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("lifecycle_audits.id", ondelete="CASCADE")
    )
    object_key: Mapped[str] = mapped_column(Text)
    attempts: Mapped[int] = mapped_column(Integer, default=0)
    last_error: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, server_default=func.now()
    )


class ProcessingJob(Base):
    __tablename__ = "processing_jobs"
    __table_args__ = (
        CheckConstraint("attempts >= 0", name="ck_processing_jobs_attempts"),
        CheckConstraint("max_attempts > 0", name="ck_processing_jobs_max_attempts"),
        Index("ix_processing_jobs_claim", "status", "next_attempt_at", "created_at"),
        Index("ix_processing_jobs_item_id", "item_id"),
        UniqueConstraint(
            "item_id",
            "analysis_version",
            name="uq_processing_jobs_item_analysis_version",
        ),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    item_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("items.id", ondelete="CASCADE")
    )
    kind: Mapped[str] = mapped_column(String(20))
    analysis_version: Mapped[int | None] = mapped_column(Integer)
    execution_backend: Mapped[str] = mapped_column(
        String(20),
        default=AnalysisExecutionBackend.DATABASE.value,
        server_default=AnalysisExecutionBackend.DATABASE.value,
    )
    reason: Mapped[str] = mapped_column(
        String(40), default="capture", server_default="capture"
    )
    temporal_workflow_id: Mapped[str | None] = mapped_column(String(255))
    stage: Mapped[str] = mapped_column(
        String(40), default="queued", server_default="queued"
    )
    stage_data: Mapped[dict[str, Any]] = mapped_column(
        JSON, default=dict, server_default="{}"
    )
    content_hash: Mapped[str | None] = mapped_column(String(64))
    cancel_requested: Mapped[bool] = mapped_column(
        Boolean, default=False, server_default="0"
    )
    correlation_id: Mapped[str] = mapped_column(String(128), default=new_uuid)
    ai_provider: Mapped[str | None] = mapped_column(String(40))
    ai_model: Mapped[str | None] = mapped_column(String(255))
    ai_policy: Mapped[dict[str, Any]] = mapped_column(
        JSON, default=dict, server_default="{}"
    )
    status: Mapped[str] = mapped_column(String(20), default="pending")
    attempts: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    max_attempts: Mapped[int] = mapped_column(Integer, default=3, server_default="3")
    next_attempt_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, server_default=func.now()
    )
    locked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_error: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, server_default=func.now()
    )
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    item: Mapped["Item"] = relationship(back_populates="processing_jobs")


class AIUsageEvent(Base):
    __tablename__ = "ai_usage_events"
    __table_args__ = (
        Index("ix_ai_usage_created", "created_at"),
        Index("ix_ai_usage_user_created", "user_id", "created_at"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    operation_key: Mapped[str] = mapped_column(String(255), unique=True)
    user_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="SET NULL")
    )
    item_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("items.id", ondelete="SET NULL")
    )
    task: Mapped[str] = mapped_column(String(40))
    provider: Mapped[str] = mapped_column(String(40))
    model: Mapped[str | None] = mapped_column(String(255))
    status: Mapped[str] = mapped_column(String(20), default="reserved")
    input_tokens: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    output_tokens: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    total_tokens: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    cost_usd: Mapped[float] = mapped_column(default=0.0, server_default="0")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, server_default=func.now()
    )
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class AIRun(Base):
    __tablename__ = "ai_runs"
    __table_args__ = (
        Index("ix_ai_runs_user_created", "user_id", "started_at"),
        Index("ix_ai_runs_item_version", "item_id", "analysis_version"),
        Index("ix_ai_runs_provider_status", "provider", "status"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    user_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="CASCADE")
    )
    item_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("items.id", ondelete="CASCADE")
    )
    analysis_version: Mapped[int | None] = mapped_column(Integer)
    job_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("processing_jobs.id", ondelete="SET NULL")
    )
    workflow_id: Mapped[str | None] = mapped_column(String(255))
    correlation_id: Mapped[str | None] = mapped_column(String(128))
    task: Mapped[str] = mapped_column(String(40))
    provider: Mapped[str] = mapped_column(String(40))
    requested_model: Mapped[str | None] = mapped_column(String(255))
    resolved_model: Mapped[str | None] = mapped_column(String(255))
    prompt_version: Mapped[str] = mapped_column(String(40), default="enrichment-v1")
    schema_version: Mapped[int] = mapped_column(Integer, default=1, server_default="1")
    content_hash: Mapped[str] = mapped_column(String(64))
    status: Mapped[str] = mapped_column(String(30), default="started")
    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, server_default=func.now()
    )
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    latency_ms: Mapped[int | None] = mapped_column(Integer)
    attempts: Mapped[int] = mapped_column(Integer, default=1, server_default="1")
    finish_reason: Mapped[str | None] = mapped_column(String(100))
    input_tokens: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    output_tokens: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    total_tokens: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    estimated_cost_usd: Mapped[float] = mapped_column(default=0.0, server_default="0")
    fallback_chain: Mapped[list[Any]] = mapped_column(
        JSON, default=list, server_default="[]"
    )
    error_code: Mapped[str | None] = mapped_column(String(100))
    encrypted_debug_payload: Mapped[str | None] = mapped_column(Text)
    debug_expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    field_provenances: Mapped[list["AIFieldProvenance"]] = relationship(
        back_populates="run", cascade="all, delete-orphan"
    )


class AdminAnalysisAction(Base):
    """Immutable, content-free audit trail for operator analysis actions."""

    __tablename__ = "admin_analysis_actions"
    __table_args__ = (
        Index("ix_admin_analysis_actions_created", "created_at"),
        Index("ix_admin_analysis_actions_job", "job_id"),
        UniqueConstraint("idempotency_key", name="uq_admin_analysis_action_key"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    actor_user_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="SET NULL")
    )
    item_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("items.id", ondelete="SET NULL")
    )
    job_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("processing_jobs.id", ondelete="SET NULL")
    )
    action: Mapped[str] = mapped_column(String(20))
    status: Mapped[str] = mapped_column(String(20))
    idempotency_key: Mapped[str] = mapped_column(String(255))
    correlation_id: Mapped[str] = mapped_column(String(128))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, server_default=func.now()
    )


class EnrichmentRecord(Base):
    """Validated structured enrichment retained per immutable analysis version."""

    __tablename__ = "enrichment_records"
    __table_args__ = (
        UniqueConstraint(
            "item_id", "analysis_version", name="uq_enrichment_item_version"
        ),
        Index("ix_enrichment_user_generated", "user_id", "generated_at"),
        Index("ix_enrichment_classification", "classification"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    user_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="CASCADE")
    )
    item_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("items.id", ondelete="CASCADE")
    )
    ai_run_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("ai_runs.id", ondelete="SET NULL")
    )
    analysis_version: Mapped[int] = mapped_column(Integer)
    schema_version: Mapped[int] = mapped_column(Integer, default=1, server_default="1")
    taxonomy_version: Mapped[int] = mapped_column(
        Integer, default=1, server_default="1"
    )
    summary: Mapped[str | None] = mapped_column(Text)
    detailed_summary: Mapped[str | None] = mapped_column(Text)
    topics: Mapped[list[Any]] = mapped_column(JSON, default=list, server_default="[]")
    suggested_tags: Mapped[list[Any]] = mapped_column(
        JSON, default=list, server_default="[]"
    )
    classification: Mapped[str | None] = mapped_column(String(100))
    entities: Mapped[list[Any]] = mapped_column(JSON, default=list, server_default="[]")
    key_phrases: Mapped[list[Any]] = mapped_column(
        JSON, default=list, server_default="[]"
    )
    content_language: Mapped[str | None] = mapped_column(String(20))
    confidence: Mapped[float | None]
    warnings: Mapped[list[Any]] = mapped_column(JSON, default=list, server_default="[]")
    provider: Mapped[str] = mapped_column(String(40))
    model: Mapped[str | None] = mapped_column(String(255))
    prompt_version: Mapped[str] = mapped_column(String(40))
    content_hash: Mapped[str] = mapped_column(String(64))
    field_provenance: Mapped[dict[str, Any]] = mapped_column(
        JSON, default=dict, server_default="{}"
    )
    generated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, server_default=func.now()
    )


class AISuggestionFeedback(Base):
    """Immutable private feedback and application event for an AI suggestion."""

    __tablename__ = "ai_suggestion_feedback"
    __table_args__ = (
        UniqueConstraint("client_id", name="uq_ai_suggestion_feedback_client"),
        Index("ix_ai_suggestion_item_version", "item_id", "analysis_version"),
        Index("ix_ai_suggestion_user_created", "user_id", "created_at"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    client_id: Mapped[str] = mapped_column(String(100))
    user_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="CASCADE")
    )
    item_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("items.id", ondelete="CASCADE")
    )
    enrichment_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("enrichment_records.id", ondelete="CASCADE")
    )
    analysis_version: Mapped[int] = mapped_column(Integer)
    suggestion_type: Mapped[str] = mapped_column(String(30))
    value: Mapped[str] = mapped_column(String(100))
    normalized_value: Mapped[str] = mapped_column(String(100))
    action: Mapped[str] = mapped_column(String(30))
    changed_item: Mapped[bool] = mapped_column(Boolean, default=False)
    item_revision_after: Mapped[int] = mapped_column(Integer)
    metadata_json: Mapped[dict[str, Any]] = mapped_column(
        "metadata", JSON, default=dict, server_default="{}"
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, server_default=func.now()
    )


class AISuggestionPreference(Base):
    __tablename__ = "ai_suggestion_preferences"
    __table_args__ = (
        UniqueConstraint(
            "user_id",
            "suggestion_type",
            "normalized_value",
            name="uq_ai_suggestion_preference",
        ),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    user_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="CASCADE")
    )
    suggestion_type: Mapped[str] = mapped_column(String(30))
    normalized_value: Mapped[str] = mapped_column(String(100))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, server_default=func.now()
    )


class AIFieldProvenance(Base):
    __tablename__ = "ai_field_provenance"
    __table_args__ = (Index("ix_ai_field_item_version", "item_id", "analysis_version"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    run_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("ai_runs.id", ondelete="CASCADE")
    )

    run: Mapped["AIRun"] = relationship(back_populates="field_provenances")
    user_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="CASCADE")
    )
    item_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("items.id", ondelete="CASCADE")
    )
    analysis_version: Mapped[int | None] = mapped_column(Integer)
    field_name: Mapped[str] = mapped_column(String(60))
    source: Mapped[str] = mapped_column(String(30))
    provider: Mapped[str] = mapped_column(String(40))
    model: Mapped[str | None] = mapped_column(String(255))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, server_default=func.now()
    )


class ItemEmbedding(Base):
    __tablename__ = "item_embeddings"
    __table_args__ = (
        UniqueConstraint(
            "item_id",
            "analysis_version",
            "chunk_id",
            "index_id",
            name="uq_item_embedding",
        ),
        Index("ix_item_embeddings_user", "user_id"),
        Index("ix_item_embeddings_index_hash", "index_id", "content_hash"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    user_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="CASCADE")
    )
    item_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("items.id", ondelete="CASCADE")
    )
    analysis_version: Mapped[int] = mapped_column(Integer)
    chunk_id: Mapped[str] = mapped_column(String(64))
    index_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("embedding_indexes.id", ondelete="RESTRICT")
    )
    provider: Mapped[str] = mapped_column(String(40))
    model: Mapped[str] = mapped_column(String(255))
    dimensions: Mapped[int] = mapped_column(Integer)
    normalization: Mapped[str] = mapped_column(String(20), default="l2")
    index_version: Mapped[int] = mapped_column(Integer, default=1, server_default="1")
    vector: Mapped[list[float]] = mapped_column(JSON)
    content_hash: Mapped[str] = mapped_column(String(64))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, server_default=func.now()
    )


class EmbeddingIndex(Base):
    __tablename__ = "embedding_indexes"
    __table_args__ = (
        UniqueConstraint(
            "provider",
            "model",
            "dimensions",
            "normalization",
            "version",
            name="uq_embedding_index_schema",
        ),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    provider: Mapped[str] = mapped_column(String(40))
    model: Mapped[str] = mapped_column(String(255))
    dimensions: Mapped[int] = mapped_column(Integer)
    normalization: Mapped[str] = mapped_column(String(20), default="l2")
    version: Mapped[int] = mapped_column(Integer, default=1, server_default="1")
    status: Mapped[str] = mapped_column(String(20), default="active")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, server_default=func.now()
    )


class DocumentChunk(Base):
    __tablename__ = "document_chunks"
    __table_args__ = (
        UniqueConstraint(
            "item_id", "analysis_version", "ordinal", name="uq_document_chunk_ordinal"
        ),
        Index("ix_document_chunk_hash", "user_id", "content_hash"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    chunk_key: Mapped[str] = mapped_column(String(100))
    user_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="CASCADE")
    )
    item_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("items.id", ondelete="CASCADE")
    )
    analysis_version: Mapped[int] = mapped_column(Integer)
    ordinal: Mapped[int] = mapped_column(Integer)
    text: Mapped[str] = mapped_column(Text)
    start_offset: Mapped[int] = mapped_column(Integer)
    end_offset: Mapped[int] = mapped_column(Integer)
    content_hash: Mapped[str] = mapped_column(String(64))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, server_default=func.now()
    )


class ItemInteraction(Base):
    __tablename__ = "item_interactions"
    __table_args__ = (
        UniqueConstraint("user_id", "client_id", name="uq_item_interaction_client"),
        Index(
            "ix_item_interaction_subject_created",
            "user_id",
            "subject_item_id",
            "created_at",
        ),
        Index("ix_item_interaction_kind_action", "user_id", "kind", "action"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    user_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="CASCADE")
    )
    subject_item_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("items.id", ondelete="CASCADE")
    )
    context_item_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("items.id", ondelete="CASCADE")
    )
    kind: Mapped[str] = mapped_column(String(30))
    action: Mapped[str] = mapped_column(String(30))
    client_id: Mapped[str | None] = mapped_column(String(100))
    reverses_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("item_interactions.id", ondelete="SET NULL")
    )
    reason_code: Mapped[str | None] = mapped_column(String(60))
    interaction_metadata: Mapped[dict[str, Any] | None] = mapped_column(
        "metadata", JSON
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, server_default=func.now()
    )
