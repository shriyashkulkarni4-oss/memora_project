"""Serializable payloads used by Temporal workflows and activities."""

from dataclasses import dataclass


@dataclass(frozen=True)
class AnalysisWorkflowInput:
    job_id: str
    item_id: str
    analysis_version: int
    item_type: str = "unknown"
    tenant_key: str = "unknown"
    provider: str = "pending"
    model: str = "pending"
    correlation_id: str = "unknown"
    search_attributes_enabled: bool = False


@dataclass(frozen=True)
class AnalysisStageOutcome:
    item_id: str
    analysis_version: int
    stage: str
    content_hash: str | None = None
    message: str | None = None


@dataclass(frozen=True)
class BackfillWorkflowInput:
    requests: tuple[AnalysisWorkflowInput, ...]
    items_per_minute: int = 30


@dataclass(frozen=True)
class BackfillWorkflowOutcome:
    total: int
    completed: int
    cancelled: bool = False


@dataclass(frozen=True)
class EmbeddingBackfillInput:
    expected_index_version: int
    max_items: int = 1_000
    items_per_minute: int = 30
    cursor: str | None = None


@dataclass(frozen=True)
class EmbeddingBackfillPageInput:
    expected_index_version: int
    cursor: str | None
    limit: int


@dataclass(frozen=True)
class EmbeddingBackfillPageOutcome:
    processed: int
    next_cursor: str | None
    exhausted: bool


@dataclass(frozen=True)
class EmbeddingBackfillOutcome:
    completed: int
    cursor: str | None
    exhausted: bool
