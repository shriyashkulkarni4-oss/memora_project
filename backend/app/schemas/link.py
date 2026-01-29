"""Link schemas."""

from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel

from app.models.models import LinkSource, LinkStatus


class TagResponse(BaseModel):
    """Schema for tag response."""
    id: str
    name: str
    color: str

    class Config:
        from_attributes = True


class AISummary(BaseModel):
    """Schema for AI-generated summary."""
    summary: str
    keyPoints: List[str]
    topics: List[str]
    suggestedCategories: List[str]
    suggestedTags: List[str]
    processedAt: datetime


class LinkCreate(BaseModel):
    """Schema for creating a link."""
    url: Optional[str] = None
    title: str
    description: Optional[str] = None
    source: LinkSource = LinkSource.MANUAL
    category_id: Optional[str] = None
    tags: Optional[List[str]] = None
    notes: Optional[str] = None


class LinkUpdate(BaseModel):
    """Schema for updating a link."""
    title: Optional[str] = None
    description: Optional[str] = None
    category_id: Optional[str] = None
    tags: Optional[List[str]] = None
    notes: Optional[str] = None
    is_favorite: Optional[bool] = None
    is_archived: Optional[bool] = None


class LinkResponse(BaseModel):
    """Schema for link response."""
    id: str
    user_id: str
    url: Optional[str]
    title: str
    description: Optional[str]
    favicon: Optional[str]
    source: LinkSource
    status: LinkStatus
    category_id: Optional[str]
    tags: List[TagResponse]
    ai_summary: Optional[dict]
    screenshot_url: Optional[str] = None
    is_favorite: bool
    is_archived: bool
    read_count: int
    last_visited_at: Optional[datetime]
    notes: Optional[str]
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class LinkListResponse(BaseModel):
    """Schema for paginated link list response."""
    links: List[LinkResponse]
    total: int
    page: int
    page_size: int
    total_pages: int


class LinkStats(BaseModel):
    """Schema for link statistics."""
    total_links: int
    favorite_links: int
    archived_links: int
    pending_processing: int
