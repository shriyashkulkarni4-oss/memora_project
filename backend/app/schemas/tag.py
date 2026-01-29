"""Tag schemas."""

from pydantic import BaseModel


class TagCreate(BaseModel):
    """Schema for creating a tag."""
    name: str
    color: str = "#6b7280"


class TagResponse(BaseModel):
    """Schema for tag response."""
    id: str
    name: str
    color: str
    usage_count: int = 0

    class Config:
        from_attributes = True
