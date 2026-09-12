"""AI suggestion review and offline-safe feedback contracts."""

from typing import Literal

from pydantic import BaseModel, Field


class SuggestionResponse(BaseModel):
    suggestion_type: Literal["tag", "classification"]
    value: str
    confidence: float | None
    status: Literal["pending", "accepted", "rejected", "never"]
    can_undo: bool = False


class SuggestionOverviewResponse(BaseModel):
    item_id: str
    analysis_version: int
    item_revision: int
    topics: list[str]
    classification: str | None
    suggestions: list[SuggestionResponse]


class SuggestionDecisionCommand(BaseModel):
    suggestion_type: Literal["tag", "classification"]
    value: str = Field(min_length=1, max_length=100)
    action: Literal["accept", "reject", "never", "undo"]


class SuggestionDecisionRequest(BaseModel):
    client_id: str = Field(min_length=1, max_length=64)
    analysis_version: int = Field(ge=1)
    expected_revision: int = Field(ge=1)
    decisions: list[SuggestionDecisionCommand] = Field(min_length=1, max_length=25)
