"""Admin API contracts."""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from app.models import ItemType, ProcessingStatus, UserRole

AdminProcessingJobStatus = Literal["pending", "processing", "completed", "failed"]


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
