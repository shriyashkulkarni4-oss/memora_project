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


class ProcessingStatus(str, enum.Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    READY = "ready"
    FAILED = "failed"
    SKIPPED = "skipped"


class AnalysisStatus(str, enum.Enum):
    NOT_ANALYZED = "not_analyzed"
    PENDING = "pending"
    ANALYZING = "analyzing"
    ANALYZED = "analyzed"
    FAILED = "failed"
    SKIPPED = "skipped"


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
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    item_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("items.id", ondelete="CASCADE")
    )
    kind: Mapped[str] = mapped_column(String(20))
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
