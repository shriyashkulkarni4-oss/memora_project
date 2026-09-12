"""Admin API contracts."""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from app.models import AnalysisStatus, ItemType, ProcessingStatus, UserRole

AdminProcessingJobStatus = Literal[
    "pending", "scheduled", "processing", "completed", "failed", "skipped", "cancelled"
]


class AdminDashboardResponse(BaseModel):
    users_total: int
    active_users: int
    disabled_users: int
    admin_users: int
    items_total: int
    archived_items: int
    assets_total: int
    storage_bytes: int
    processing_pending: int
    processing_failed: int
    analysis_pending: int
    analysis_failed: int


class AIProviderHealthResponse(BaseModel):
    provider: Literal["ollama", "openrouter", "huggingface", "n8n", "openai_compatible"]
    available: bool
    latency_ms: int | None = None
    message: str | None = None
    capabilities: list[str]


class AIProviderConfiguration(BaseModel):
    provider: Literal["ollama", "openrouter", "huggingface", "n8n", "openai_compatible"]
    enabled: bool
    credential_configured: bool
    deployment_type: Literal["local", "self_hosted", "third_party"]


class AITaskConfiguration(BaseModel):
    primary: str | None
    fallbacks: list[str]


class AdminAIConfigurationResponse(BaseModel):
    tasks: dict[str, AITaskConfiguration]
    cross_provider_fallback_enabled: bool
    external_content_allowed: bool
    allowed_external_providers: list[str]
    budgets: dict[str, float]
    providers: list[AIProviderConfiguration]


class AdminAIRunResponse(BaseModel):
    id: str
    item_id: str | None
    analysis_version: int | None
    workflow_id: str | None
    correlation_id: str | None
    task: str
    provider: str
    requested_model: str | None
    resolved_model: str | None
    prompt_version: str
    schema_version: int
    content_hash: str
    status: str
    started_at: datetime
    completed_at: datetime | None
    latency_ms: int | None
    attempts: int
    finish_reason: str | None
    input_tokens: int
    output_tokens: int
    total_tokens: int
    estimated_cost_usd: float
    fallback_chain: list[str]
    error_code: str | None


class AdminAIRunsPage(BaseModel):
    runs: list[AdminAIRunResponse]
    total: int
    limit: int = Field(ge=1)
    offset: int = Field(ge=0)


class AdminAnalysisProviderMetric(BaseModel):
    provider: str
    runs: int
    successes: int
    failures: int
    average_latency_ms: float | None


class AdminAnalysisRecentError(BaseModel):
    item_reference: str
    job_id: str | None
    workflow_id: str | None
    correlation_id: str | None
    stage: str
    provider: str | None
    code: str
    occurred_at: datetime


class AdminAnalysisRunSummary(BaseModel):
    item_id: str
    item_reference: str
    job_id: str
    workflow_id: str | None
    correlation_id: str
    analysis_version: int | None
    backend: Literal["database", "temporal"]
    stage: str
    provider: str | None
    model_alias: str | None
    status: AdminProcessingJobStatus
    analysis_status: AnalysisStatus
    enrichment_mode: Literal["ai", "deterministic", "no_enrichment"]
    attempts: int
    max_attempts: int
    created_at: datetime
    updated_at: datetime
    completed_at: datetime | None
    error_code: str | None


class AdminAnalysisOperationsResponse(BaseModel):
    queue_depth: int
    oldest_pending_age_seconds: float | None
    status_counts: dict[str, int]
    stage_counts: dict[str, int]
    throughput_24h: int
    success_rate_24h: float
    degraded_rate_24h: float
    temporal_enabled: bool
    temporal_ui_url: str | None
    providers: list[AdminAnalysisProviderMetric]
    recent_errors: list[AdminAnalysisRecentError]
    recent_runs: list[AdminAnalysisRunSummary]


class AdminAnalysisActionRequest(BaseModel):
    confirmation: Literal["RETRY", "CANCEL", "REANALYZE"]


class AdminUserResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    email: str
    name: str | None
    role: UserRole
    is_active: bool
    item_count: int = 0
    asset_count: int = 0
    storage_bytes: int = 0
    created_at: datetime
    updated_at: datetime


class AdminUserUpdate(BaseModel):
    role: UserRole | None = None
    is_active: bool | None = None


class AdminUsersPage(BaseModel):
    users: list[AdminUserResponse]
    total: int
    limit: int = Field(ge=1)
    offset: int = Field(ge=0)


class AdminBackupRecord(BaseModel):
    path: str
    created_at: datetime
    size_bytes: int
    has_postgres_dump: bool
    has_minio_dir: bool
    has_checksums: bool


class AdminBackupStatusResponse(BaseModel):
    configured: bool
    command: str | None
    backup_root: str
    retention_days: int
    latest: AdminBackupRecord | None
    recent: list[AdminBackupRecord]


class AdminBackupRunResponse(BaseModel):
    status: Literal["succeeded"]
    exit_code: int
    stdout: str
    stderr: str
    latest: AdminBackupRecord | None
    duration_seconds: float


class AdminProcessingJobResponse(BaseModel):
    id: str
    item_id: str
    item_title: str | None
    item_type: ItemType
    item_processing_status: ProcessingStatus
    analysis_version: int | None
    execution_backend: Literal["database", "temporal"]
    reason: str
    temporal_workflow_id: str | None
    stage: str
    content_hash: str | None
    correlation_id: str
    ai_provider: str | None
    ai_model: str | None
    cancel_requested: bool
    user_id: str
    user_email: str
    status: AdminProcessingJobStatus
    attempts: int
    max_attempts: int
    next_attempt_at: datetime
    locked_at: datetime | None
    last_error: str | None
    created_at: datetime
    updated_at: datetime
    completed_at: datetime | None


class AdminProcessingJobsPage(BaseModel):
    jobs: list[AdminProcessingJobResponse]
    total: int
    limit: int = Field(ge=1)
    offset: int = Field(ge=0)
