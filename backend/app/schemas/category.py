"""Category schemas."""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel


class CategoryCreate(BaseModel):
    """Schema for creating a category."""

    name: str
    color: str = "#3b82f6"
    icon: str = "FolderOpen"
    description: Optional[str] = None


class CategoryUpdate(BaseModel):
    """Schema for updating a category."""

    name: Optional[str] = None
    color: Optional[str] = None
    icon: Optional[str] = None
    description: Optional[str] = None


class CategoryResponse(BaseModel):
    """Schema for category response."""

    id: str
    name: str
    color: str
    icon: str
    description: Optional[str]
    link_count: int = 0
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
