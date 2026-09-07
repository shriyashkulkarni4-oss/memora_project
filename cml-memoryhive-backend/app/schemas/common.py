"""Shared API response contracts."""

from typing import Any

from pydantic import BaseModel, Field


class ErrorDetail(BaseModel):
    code: str
    message: str
    details: dict[str, Any] | list[Any] | None = None


class ErrorResponse(BaseModel):
    error: ErrorDetail


class CursorPage(BaseModel):
    next_cursor: str | None = None
    has_more: bool = False
    limit: int = Field(ge=1, le=100)
