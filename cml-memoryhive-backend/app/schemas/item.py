"""Versioned Item API schemas."""

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import (
    AnyHttpUrl,
    BaseModel,
    ConfigDict,
    Field,
    field_validator,
    model_validator,
)

from app.models import AnalysisStatus, ItemType, ProcessingStatus


class TagReference(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    name: str
    color: str


class AssetResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    mime_type: str
    size_bytes: int
    original_filename: str | None = None
    sha256: str | None = None
    width: int | None = None
    height: int | None = None
    created_at: datetime


class ItemCreate(BaseModel):
    """Capture payload. A supplied UUID makes offline capture idempotent."""

    id: UUID | None = None
    type: ItemType
    url: AnyHttpUrl | None = None
    raw_text: str | None = Field(default=None, max_length=1_000_000)
    title: str | None = Field(default=None, max_length=500)
    description: str | None = Field(default=None, max_length=20_000)
    notes: str | None = Field(default=None, max_length=100_000)
    source: str | None = Field(default=None, max_length=100)
    category_id: UUID | None = None
    tags: list[str] = Field(default_factory=list, max_length=50)
    metadata: dict[str, Any] | None = None
    created_at: datetime | None = None

    @field_validator("raw_text", "title", "description", "notes", "source")
    @classmethod
    def strip_optional_text(cls, value: str | None) -> str | None:
        if value is None:
            return None
        normalized = value.strip()
        return normalized or None

    @field_validator("tags")
    @classmethod
    def normalize_tags(cls, tags: list[str]) -> list[str]:
        normalized = {tag.strip().lower() for tag in tags if tag.strip()}
        if any(len(tag) > 50 for tag in normalized):
            raise ValueError("tag names must be 50 characters or fewer")
        return sorted(normalized)

    @model_validator(mode="after")
    def require_variant_content(self) -> "ItemCreate":
        if self.type == ItemType.LINK and self.url is None:
            raise ValueError("url is required for link items")
        if self.type == ItemType.TEXT and self.raw_text is None:
            raise ValueError("raw_text is required for text items")
        return self


class ItemUpdate(BaseModel):
    expected_revision: int | None = Field(default=None, ge=1)
    url: AnyHttpUrl | None = None
    raw_text: str | None = Field(default=None, max_length=1_000_000)
    title: str | None = Field(default=None, max_length=500)
    description: str | None = Field(default=None, max_length=20_000)
    notes: str | None = Field(default=None, max_length=100_000)
    source: str | None = Field(default=None, max_length=100)
    category_id: UUID | None = None
    tags: list[str] | None = Field(default=None, max_length=50)
    is_favorite: bool | None = None
    is_archived: bool | None = None

    @field_validator("tags")
    @classmethod
    def normalize_tags(cls, tags: list[str] | None) -> list[str] | None:
        if tags is None:
            return None
        normalized = {tag.strip().lower() for tag in tags if tag.strip()}
        if any(len(tag) > 50 for tag in normalized):
            raise ValueError("tag names must be 50 characters or fewer")
        return sorted(normalized)


class ItemResponse(BaseModel):
    id: str
    user_id: str
    type: ItemType
    url: str | None
    raw_text: str | None
    title: str | None
    description: str | None
    notes: str | None
    source: str | None
    source_domain: str | None
    author: str | None
    published_at: datetime | None
    favicon_url: str | None
    extracted_text: str | None
    language: str | None
    summary: str | None
    metadata: dict[str, Any] | None
    processing_status: ProcessingStatus
    processing_error: str | None
    analysis_status: AnalysisStatus
    analysis_error: str | None
    analysis_version: int
    analysis_requested_at: datetime | None
    analysis_started_at: datetime | None
    analysis_completed_at: datetime | None
    category_id: str | None
    tags: list[TagReference]
    assets: list[AssetResponse]
    is_favorite: bool
    is_archived: bool
    read_count: int
    last_visited_at: datetime | None
    revision: int
    deleted_at: datetime | None
    created_at: datetime
    updated_at: datetime


class ItemListResponse(BaseModel):
    items: list[ItemResponse]
    next_cursor: str | None = None
    has_more: bool
    limit: int


class ItemChangesResponse(BaseModel):
    items: list[ItemResponse]
    next_cursor: str | None = None
    has_more: bool
    server_time: datetime


class ItemMutationResponse(BaseModel):
    id: str
    revision: int
    updated_at: datetime


class ItemStats(BaseModel):
    total_items: int
    active_items: int
    favorite_items: int
    archived_items: int
    pending_processing: int
    failed_processing: int
    pending_analysis: int
    failed_analysis: int
    by_type: dict[ItemType, int]


class ProcessingStateResponse(BaseModel):
    item_id: str
    status: ProcessingStatus
    error: str | None
    updated_at: datetime
