"""Category contracts."""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator


class CategoryCreate(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    color: str = Field(default="#3b82f6", pattern=r"^#[0-9a-fA-F]{6}$")
    icon: str = Field(default="folder", max_length=50)
    description: str | None = Field(default=None, max_length=2_000)

    @field_validator("name")
    @classmethod
    def normalize_name(cls, name: str) -> str:
        return " ".join(name.split())


class CategoryUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=100)
    color: str | None = Field(default=None, pattern=r"^#[0-9a-fA-F]{6}$")
    icon: str | None = Field(default=None, max_length=50)
    description: str | None = Field(default=None, max_length=2_000)


class CategoryResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    name: str
    color: str
    icon: str
    description: str | None
    item_count: int = 0
    created_at: datetime
    updated_at: datetime
