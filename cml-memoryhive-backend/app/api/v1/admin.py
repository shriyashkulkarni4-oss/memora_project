"""Administrative dashboards, analysis operations, and access management."""

import re
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy import func, select
from temporalio.client import Client

from app.ai.factory import build_ai_gateway
from app.ai.gateway import ProviderError
from app.config import get_settings
from app.core.deps import CurrentAdmin, DbSession
from app.models import (
    AdminAnalysisAction,
    AIRun,
    AnalysisStatus,
    Asset,
    Item,
    ItemType,
    ProcessingJob,
    ProcessingStatus,
    User,
    UserRole,
)
from app.schemas.admin import (
    AdminAIConfigurationResponse,
    AdminAIRunResponse,
    AdminAIRunsPage,
    AdminAnalysisActionRequest,
    AdminAnalysisOperationsResponse,
    AdminAnalysisProviderMetric,
    AdminAnalysisRecentError,
    AdminAnalysisRunSummary,
    AdminBackupRecord,
    AdminBackupRunResponse,
    AdminBackupStatusResponse,
    AdminDashboardResponse,
    AdminProcessingJobResponse,
    AdminProcessingJobsPage,
    AdminProcessingJobStatus,
    AdminUserResponse,
    AdminUsersPage,
    AdminUserUpdate,
    AIProviderConfiguration,
    AIProviderHealthResponse,
    AITaskConfiguration,
)
from app.schemas.common import ErrorResponse
from app.services.account_lifecycle import delete_user_account
from app.services.analysis_dispatch import retry_item_analysis
from app.services.backup import (
    BackupCommandError,
    BackupCommandTimeoutError,
    BackupNotConfiguredError,
    BackupRecord,
    backup_status,
    run_backup,
)
from app.services.storage import StorageService, get_storage_service
from app.temporal_pipeline.workflows import AnalyzeItemWorkflow

router = APIRouter()
Storage = Annotated[StorageService, Depends(get_storage_service)]

ERRORS = {
    400: {"model": ErrorResponse},
    401: {"model": ErrorResponse},
    403: {"model": ErrorResponse},
    404: {"model": ErrorResponse},
    422: {"model": ErrorResponse},
}


@router.get(
    "/ai/config",
    response_model=AdminAIConfigurationResponse,
    responses=ERRORS,
)
async def ai_configuration(_admin: CurrentAdmin) -> AdminAIConfigurationResponse:
    """Return routing controls and credential presence, never credential values."""
    settings = get_settings()
    tasks = {
        name: AITaskConfiguration(
            primary=getattr(settings, f"ai_{name}_route"),
            fallbacks=getattr(settings, f"ai_{name}_fallback_routes"),
        )
        for name in ("summarization", "enrichment", "embeddings", "reranking", "vision")
    }
    providers = [
        AIProviderConfiguration(
            provider="ollama",
            enabled=bool(settings.ollama_base_url),
            credential_configured=False,
            deployment_type=settings.ollama_deployment_type,
        ),
        AIProviderConfiguration(
            provider="n8n",
            enabled=bool(settings.n8n_webhook_url),
            credential_configured=bool(
                settings.n8n_api_key or settings.n8n_signing_secret
            ),
            deployment_type=settings.n8n_deployment_type,
        ),
        AIProviderConfiguration(
            provider="openrouter",
            enabled=settings.openrouter_enabled,
            credential_configured=bool(settings.openrouter_api_key),
            deployment_type="third_party",
        ),
        AIProviderConfiguration(
            provider="huggingface",
            enabled=settings.huggingface_enabled,
            credential_configured=bool(settings.huggingface_token),
            deployment_type="third_party",
        ),
        AIProviderConfiguration(
            provider="openai_compatible",
            enabled=settings.openai_compatible_enabled,
            credential_configured=bool(settings.openai_compatible_api_key),
            deployment_type=settings.openai_compatible_deployment_type,
        ),
    ]
    return AdminAIConfigurationResponse(
        tasks=tasks,
        cross_provider_fallback_enabled=settings.ai_cross_provider_fallback_enabled,
        external_content_allowed=settings.ai_external_content_allowed,
        allowed_external_providers=settings.ai_allowed_external_providers,
        budgets={
            "daily_requests": settings.ai_daily_request_budget,
            "monthly_requests": settings.ai_monthly_request_budget,
            "daily_tokens": settings.ai_daily_token_budget,
            "monthly_tokens": settings.ai_monthly_token_budget,
            "daily_cost_usd": settings.ai_daily_cost_budget_usd,
            "monthly_cost_usd": settings.ai_monthly_cost_budget_usd,
            "per_user_daily_requests": settings.ai_per_user_daily_request_quota,
            "per_user_monthly_requests": settings.ai_per_user_monthly_request_quota,
            "per_user_daily_tokens": settings.ai_per_user_daily_token_quota,
            "per_user_monthly_tokens": settings.ai_per_user_monthly_token_quota,
        },
        providers=providers,
    )


@router.get("/ai/runs", response_model=AdminAIRunsPage, responses=ERRORS)
async def ai_runs(
    _admin: CurrentAdmin,
    db: DbSession,
    provider: str | None = Query(default=None, max_length=40),
    task: str | None = Query(default=None, max_length=40),
    run_status: str | None = Query(default=None, max_length=30, alias="status"),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
) -> AdminAIRunsPage:
    conditions = []
    if provider:
        conditions.append(AIRun.provider == provider)
    if task:
        conditions.append(AIRun.task == task)
    if run_status:
        conditions.append(AIRun.status == run_status)
    total = await _count(db, AIRun, *conditions)
    records = list(
        await db.scalars(
            select(AIRun)
            .where(*conditions)
            .order_by(AIRun.started_at.desc(), AIRun.id.desc())
            .limit(limit)
            .offset(offset)
        )
    )
    return AdminAIRunsPage(
        runs=[
            AdminAIRunResponse.model_validate(record, from_attributes=True)
            for record in records
        ],
        total=total,
        limit=limit,
        offset=offset,
    )


@router.get(
    "/ai/providers/health",
    response_model=list[AIProviderHealthResponse],
    responses=ERRORS,
)
async def ai_provider_health(_admin: CurrentAdmin) -> list[AIProviderHealthResponse]:
    gateway = build_ai_gateway(get_settings())
    results: list[AIProviderHealthResponse] = []
    for provider, adapter in gateway.adapters.items():
        try:
            health = await gateway.health(provider)
            results.append(
                AIProviderHealthResponse(
                    provider=provider.value,
                    available=health.available,
                    latency_ms=health.latency_ms,
                    message=health.message,
                    capabilities=sorted(value.value for value in adapter.capabilities),
                )
            )
        except ProviderError as exc:
            results.append(
                AIProviderHealthResponse(
                    provider=provider.value,
                    available=False,
                    message=exc.code.value,
                    capabilities=sorted(value.value for value in adapter.capabilities),
                )
            )
    return results


async def _count(db: DbSession, model: type[object], *conditions: object) -> int:
    value = await db.scalar(select(func.count()).select_from(model).where(*conditions))
    return value or 0


def _admin_user_response(
    user: User,
    *,
    item_count: int = 0,
    asset_count: int = 0,
    storage_bytes: int = 0,
) -> AdminUserResponse:
    return AdminUserResponse(
        id=user.id,
        email=user.email,
        name=user.name,
        role=user.role,
        is_active=user.is_active,
        item_count=item_count,
        asset_count=asset_count,
        storage_bytes=storage_bytes,
        created_at=user.created_at,
        updated_at=user.updated_at,
    )


def _backup_record_response(record: BackupRecord) -> AdminBackupRecord:
    return AdminBackupRecord(
        path=record.path,
        created_at=record.created_at,
        size_bytes=record.size_bytes,
        has_postgres_dump=record.has_postgres_dump,
        has_minio_dir=record.has_minio_dir,
        has_checksums=record.has_checksums,
    )


def _item_display_title(item: Item) -> str | None:
    if item.title:
        return item.title
    if item.url:
        return item.url
    if item.raw_text:
        return item.raw_text[:80]
    return None


def _processing_job_response(
    job: ProcessingJob, item: Item, user: User
) -> AdminProcessingJobResponse:
    return AdminProcessingJobResponse(
        id=job.id,
        item_id=item.id,
        item_title=_item_display_title(item),
        item_type=ItemType(item.type),
        item_processing_status=ProcessingStatus(item.processing_status),
        analysis_version=job.analysis_version,
        execution_backend=job.execution_backend,
        reason=job.reason,
        temporal_workflow_id=job.temporal_workflow_id,
        stage=job.stage,
        content_hash=job.content_hash,
        correlation_id=job.correlation_id,
        ai_provider=job.ai_provider,
        ai_model=job.ai_model,
        cancel_requested=job.cancel_requested,
        user_id=user.id,
        user_email=user.email,
        status=job.status,
        attempts=job.attempts,
        max_attempts=job.max_attempts,
        next_attempt_at=job.next_attempt_at,
        locked_at=job.locked_at,
        last_error=job.last_error,
        created_at=job.created_at,
        updated_at=job.updated_at,
        completed_at=job.completed_at,
    )


async def _load_processing_job_context(
    db: DbSession, job_id: str
) -> tuple[ProcessingJob, Item, User] | None:
    row = (
        await db.execute(
            select(ProcessingJob, Item, User)
            .join(Item, ProcessingJob.item_id == Item.id)
            .join(User, Item.user_id == User.id)
            .where(ProcessingJob.id == job_id)
        )
    ).one_or_none()
    if row is None:
        return None
    job, item, user = row
    return job, item, user


def _item_reference(item: Item) -> str:
    """Return a tenant-safe operator reference with no captured content."""
    return f"{ItemType(item.type).value}:{item.id[:8]}"


def _safe_error_code(value: str | None) -> str | None:
    """Reduce arbitrary provider/job errors to a bounded diagnostic category."""
    if not value:
        return None
    normalized = value.lower()
    categories = (
        ("timeout", "timeout"),
        ("rate", "rate_limited"),
        ("auth", "authentication_failed"),
        ("credential", "authentication_failed"),
        ("budget", "budget_exceeded"),
        ("quota", "quota_exceeded"),
        ("cancel", "cancelled"),
        ("schema", "invalid_response"),
        ("circuit", "circuit_open"),
        ("unavailable", "provider_unavailable"),
    )
    for marker, code in categories:
        if marker in normalized:
            return code
    safe_code = re.sub(r"[^a-z0-9_]+", "_", normalized).strip("_")
    if safe_code and len(safe_code) <= 60 and " " not in value.strip():
        return safe_code
    return "processing_failed"


async def _record_analysis_action(
    db: DbSession,
    *,
    admin_id: str,
    item_id: str,
    job_id: str | None,
    action: str,
    version: int | None,
    correlation_id: str,
) -> AdminAnalysisAction:
    key = f"{action}:{job_id or item_id}:{version or 0}"
    existing = await db.scalar(
        select(AdminAnalysisAction).where(AdminAnalysisAction.idempotency_key == key)
    )
    if existing:
        return existing
    record = AdminAnalysisAction(
        actor_user_id=admin_id,
        item_id=item_id,
        job_id=job_id,
        action=action,
        status="accepted",
        idempotency_key=key,
        correlation_id=correlation_id,
    )
    db.add(record)
    return record


@router.get(
    "/analysis/operations",
    response_model=AdminAnalysisOperationsResponse,
    responses=ERRORS,
)
async def analysis_operations(
    _admin: CurrentAdmin, db: DbSession
) -> AdminAnalysisOperationsResponse:
    """Return content-free operational state derived from durable records."""
    now = datetime.now(timezone.utc)
    since = now - timedelta(hours=24)
    status_rows = (
        await db.execute(
            select(ProcessingJob.status, func.count(ProcessingJob.id)).group_by(
                ProcessingJob.status
            )
        )
    ).all()
    stage_rows = (
        await db.execute(
            select(ProcessingJob.stage, func.count(ProcessingJob.id)).group_by(
                ProcessingJob.stage
            )
        )
    ).all()
    active_statuses = ("pending", "scheduled", "processing")
    oldest = await db.scalar(
        select(func.min(ProcessingJob.created_at)).where(
            ProcessingJob.status.in_(active_statuses)
        )
    )
    completed_24h = list(
        await db.scalars(
            select(ProcessingJob).where(
                ProcessingJob.completed_at.is_not(None),
                ProcessingJob.completed_at >= since,
            )
        )
    )
    completed_item_ids = {job.item_id for job in completed_24h}
    degraded_count = 0
    if completed_item_ids:
        degraded_count = await _count(
            db,
            Item,
            Item.id.in_(completed_item_ids),
            Item.analysis_status == AnalysisStatus.DEGRADED.value,
        )
    successful = sum(job.status == "completed" for job in completed_24h)
    denominator = len(completed_24h)

    ai_runs_24h = list(await db.scalars(select(AIRun).where(AIRun.started_at >= since)))
    provider_runs: dict[str, list[AIRun]] = defaultdict(list)
    for run in ai_runs_24h:
        provider_runs[run.provider].append(run)
    providers = []
    for provider, runs in sorted(provider_runs.items()):
        latencies = [run.latency_ms for run in runs if run.latency_ms is not None]
        providers.append(
            AdminAnalysisProviderMetric(
                provider=provider,
                runs=len(runs),
                successes=sum(run.status == "completed" for run in runs),
                failures=sum(run.status == "failed" for run in runs),
                average_latency_ms=(
                    sum(latencies) / len(latencies) if latencies else None
                ),
            )
        )

    recent_rows = (
        await db.execute(
            select(ProcessingJob, Item)
            .join(Item, ProcessingJob.item_id == Item.id)
            .order_by(ProcessingJob.updated_at.desc(), ProcessingJob.id.desc())
            .limit(50)
        )
    ).all()
    job_ids = [job.id for job, _item in recent_rows]
    latest_runs: dict[str, AIRun] = {}
    if job_ids:
        runs = list(
            await db.scalars(
                select(AIRun)
                .where(AIRun.job_id.in_(job_ids))
                .order_by(AIRun.started_at.desc(), AIRun.id.desc())
            )
        )
        for run in runs:
            if run.job_id:
                latest_runs.setdefault(run.job_id, run)

    recent_runs = []
    recent_errors = []
    for job, item in recent_rows:
        ai_run = latest_runs.get(job.id)
        provider = ai_run.provider if ai_run else job.ai_provider
        error_code = _safe_error_code(
            ai_run.error_code if ai_run and ai_run.error_code else job.last_error
        )
        if ai_run and ai_run.provider != "deterministic":
            enrichment_mode = "ai"
        elif ai_run and ai_run.provider == "deterministic":
            enrichment_mode = "deterministic"
        else:
            enrichment_mode = "no_enrichment"
        reference = _item_reference(item)
        recent_runs.append(
            AdminAnalysisRunSummary(
                item_id=item.id,
                item_reference=reference,
                job_id=job.id,
                workflow_id=job.temporal_workflow_id,
                correlation_id=job.correlation_id,
                analysis_version=job.analysis_version,
                backend=job.execution_backend,
                stage=job.stage,
                provider=provider,
                model_alias=(ai_run.requested_model if ai_run else job.ai_model),
                status=job.status,
                analysis_status=AnalysisStatus(item.analysis_status),
                enrichment_mode=enrichment_mode,
                attempts=job.attempts,
                max_attempts=job.max_attempts,
                created_at=job.created_at,
                updated_at=job.updated_at,
                completed_at=job.completed_at,
                error_code=error_code,
            )
        )
        if error_code and len(recent_errors) < 10:
            recent_errors.append(
                AdminAnalysisRecentError(
                    item_reference=reference,
                    job_id=job.id,
                    workflow_id=job.temporal_workflow_id,
                    correlation_id=job.correlation_id,
                    stage=job.stage,
                    provider=provider,
                    code=error_code,
                    occurred_at=job.updated_at,
                )
            )

    status_counts = {str(key): int(value) for key, value in status_rows}
    queue_depth = sum(status_counts.get(value, 0) for value in active_statuses)
    if oldest and oldest.tzinfo is None:
        oldest = oldest.replace(tzinfo=timezone.utc)
    return AdminAnalysisOperationsResponse(
        queue_depth=queue_depth,
        oldest_pending_age_seconds=(
            max(0.0, (now - oldest).total_seconds()) if oldest else None
        ),
        status_counts=status_counts,
        stage_counts={str(key): int(value) for key, value in stage_rows},
        throughput_24h=denominator,
        success_rate_24h=(successful / denominator if denominator else 0.0),
        degraded_rate_24h=(degraded_count / denominator if denominator else 0.0),
        temporal_enabled=get_settings().temporal_enabled,
        temporal_ui_url=get_settings().temporal_ui_url,
        providers=providers,
        recent_errors=recent_errors,
        recent_runs=recent_runs,
    )


@router.get("/dashboard", response_model=AdminDashboardResponse, responses=ERRORS)
async def get_admin_dashboard(
    _admin: CurrentAdmin, db: DbSession
) -> AdminDashboardResponse:
    storage_bytes = await db.scalar(
        select(func.coalesce(func.sum(Asset.size_bytes), 0))
    )
    return AdminDashboardResponse(
        users_total=await _count(db, User),
        active_users=await _count(db, User, User.is_active.is_(True)),
        disabled_users=await _count(db, User, User.is_active.is_(False)),
        admin_users=await _count(db, User, User.role == UserRole.ADMIN.value),
        items_total=await _count(db, Item, Item.deleted_at.is_(None)),
        archived_items=await _count(
            db, Item, Item.deleted_at.is_(None), Item.is_archived.is_(True)
        ),
        assets_total=await _count(db, Asset),
        storage_bytes=int(storage_bytes or 0),
        processing_pending=await _count(
            db,
            ProcessingJob,
            ProcessingJob.status.in_(["pending", "processing"]),
        ),
        processing_failed=await _count(
            db,
            ProcessingJob,
            ProcessingJob.status == ProcessingStatus.FAILED.value,
        ),
        analysis_pending=await _count(
            db,
            Item,
            Item.deleted_at.is_(None),
            Item.analysis_status.in_(
                [
                    AnalysisStatus.PENDING.value,
                    AnalysisStatus.SCHEDULED.value,
                    AnalysisStatus.ANALYZING.value,
                ]
            ),
        ),
        analysis_failed=await _count(
            db,
            Item,
            Item.deleted_at.is_(None),
            Item.analysis_status == AnalysisStatus.FAILED.value,
        ),
    )


@router.get("/users", response_model=AdminUsersPage, responses=ERRORS)
async def list_admin_users(
    _admin: CurrentAdmin,
    db: DbSession,
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
) -> AdminUsersPage:
    item_counts = (
        select(Item.user_id, func.count(Item.id).label("item_count"))
        .where(Item.deleted_at.is_(None))
        .group_by(Item.user_id)
        .subquery()
    )
    asset_counts = (
        select(
            Asset.user_id,
            func.count(Asset.id).label("asset_count"),
            func.coalesce(func.sum(Asset.size_bytes), 0).label("storage_bytes"),
        )
        .group_by(Asset.user_id)
        .subquery()
    )
    rows = (
        await db.execute(
            select(
                User,
                func.coalesce(item_counts.c.item_count, 0),
                func.coalesce(asset_counts.c.asset_count, 0),
                func.coalesce(asset_counts.c.storage_bytes, 0),
            )
            .outerjoin(item_counts, item_counts.c.user_id == User.id)
            .outerjoin(asset_counts, asset_counts.c.user_id == User.id)
            .order_by(User.created_at.desc(), User.email.asc())
            .offset(offset)
            .limit(limit)
        )
    ).all()
    users = [
        _admin_user_response(
            user,
            item_count=int(item_count),
            asset_count=int(asset_count),
            storage_bytes=int(storage_bytes),
        )
        for user, item_count, asset_count, storage_bytes in rows
    ]
    return AdminUsersPage(
        users=users,
        total=await _count(db, User),
        limit=limit,
        offset=offset,
    )


@router.get("/backup", response_model=AdminBackupStatusResponse, responses=ERRORS)
async def get_admin_backup_status(_admin: CurrentAdmin) -> AdminBackupStatusResponse:
    status_snapshot = backup_status(get_settings())
    recent = [_backup_record_response(record) for record in status_snapshot.recent]
    return AdminBackupStatusResponse(
        configured=status_snapshot.configured,
        command=status_snapshot.command,
        backup_root=status_snapshot.backup_root,
        retention_days=status_snapshot.retention_days,
        latest=recent[0] if recent else None,
        recent=recent,
    )


@router.post(
    "/backup/run",
    response_model=AdminBackupRunResponse,
    responses={**ERRORS, 503: {"model": ErrorResponse}, 504: {"model": ErrorResponse}},
)
async def run_admin_backup(_admin: CurrentAdmin) -> AdminBackupRunResponse:
    try:
        result = await run_backup(get_settings())
    except BackupNotConfiguredError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except BackupCommandTimeoutError as exc:
        raise HTTPException(status_code=504, detail=str(exc)) from exc
    except BackupCommandError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    return AdminBackupRunResponse(
        status="succeeded",
        exit_code=result.exit_code,
        stdout=result.stdout,
        stderr=result.stderr,
        latest=_backup_record_response(result.latest) if result.latest else None,
        duration_seconds=result.duration_seconds,
    )


@router.get(
    "/processing/jobs",
    response_model=AdminProcessingJobsPage,
    responses=ERRORS,
)
async def list_admin_processing_jobs(
    _admin: CurrentAdmin,
    db: DbSession,
    job_status: Annotated[
        AdminProcessingJobStatus | None, Query(alias="status")
    ] = None,
    limit: int = Query(default=25, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
) -> AdminProcessingJobsPage:
    conditions = []
    if job_status:
        conditions.append(ProcessingJob.status == job_status)

    query = (
        select(ProcessingJob, Item, User)
        .join(Item, ProcessingJob.item_id == Item.id)
        .join(User, Item.user_id == User.id)
        .order_by(ProcessingJob.updated_at.desc(), ProcessingJob.created_at.desc())
        .offset(offset)
        .limit(limit)
    )
    if conditions:
        query = query.where(*conditions)

    rows = (await db.execute(query)).all()
    return AdminProcessingJobsPage(
        jobs=[_processing_job_response(job, item, user) for job, item, user in rows],
        total=await _count(db, ProcessingJob, *conditions),
        limit=limit,
        offset=offset,
    )


@router.post(
    "/processing/jobs/{job_id}/retry",
    response_model=AdminProcessingJobResponse,
    responses={**ERRORS, 409: {"model": ErrorResponse}},
)
async def retry_admin_processing_job(
    job_id: str,
    data: AdminAnalysisActionRequest,
    admin: CurrentAdmin,
    db: DbSession,
) -> AdminProcessingJobResponse:
    if data.confirmation != "RETRY":
        raise HTTPException(status_code=400, detail="RETRY confirmation is required")
    row = await _load_processing_job_context(db, job_id)
    if row is None:
        raise HTTPException(status_code=404, detail="Processing job not found")
    job, item, _user = row
    previous_action = await db.scalar(
        select(AdminAnalysisAction).where(
            AdminAnalysisAction.idempotency_key
            == f"retry:{job.id}:{job.analysis_version or 0}"
        )
    )
    if previous_action:
        latest = await db.scalar(
            select(ProcessingJob)
            .where(ProcessingJob.item_id == item.id)
            .order_by(ProcessingJob.analysis_version.desc())
        )
        if latest:
            latest_row = await _load_processing_job_context(db, latest.id)
            if latest_row:
                return _processing_job_response(*latest_row)
    if job.status != "failed":
        raise HTTPException(
            status_code=409, detail="Only failed processing jobs can be retried"
        )
    if item.deleted_at is not None:
        raise HTTPException(status_code=400, detail="Deleted items cannot be retried")
    try:
        next_job = await retry_item_analysis(
            db, item, reason="admin_retry", settings=get_settings()
        )
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    await db.flush()
    await _record_analysis_action(
        db,
        admin_id=admin.id,
        item_id=item.id,
        job_id=job.id,
        action="retry",
        version=job.analysis_version,
        correlation_id=next_job.correlation_id,
    )
    next_job_id = next_job.id
    await db.commit()

    next_row = await _load_processing_job_context(db, next_job_id)
    if next_row is None:
        raise HTTPException(status_code=404, detail="Retried job was not found")
    return _processing_job_response(*next_row)


@router.post(
    "/processing/jobs/{job_id}/cancel",
    response_model=AdminProcessingJobResponse,
    responses={**ERRORS, 409: {"model": ErrorResponse}, 503: {"model": ErrorResponse}},
)
async def cancel_admin_processing_job(
    job_id: str,
    data: AdminAnalysisActionRequest,
    admin: CurrentAdmin,
    db: DbSession,
) -> AdminProcessingJobResponse:
    if data.confirmation != "CANCEL":
        raise HTTPException(status_code=400, detail="CANCEL confirmation is required")
    row = await _load_processing_job_context(db, job_id)
    if row is None:
        raise HTTPException(status_code=404, detail="Processing job not found")
    job, item, _user = row
    if job.cancel_requested or job.status == "cancelled":
        return _processing_job_response(*row)
    if job.status not in ("pending", "scheduled", "processing"):
        raise HTTPException(status_code=409, detail="Processing job is not active")

    if job.execution_backend == "temporal":
        if not job.temporal_workflow_id:
            raise HTTPException(
                status_code=409, detail="Temporal workflow is not assigned"
            )
        settings = get_settings()
        try:
            client = await Client.connect(
                settings.temporal_address, namespace=settings.temporal_namespace
            )
            await client.get_workflow_handle(job.temporal_workflow_id).signal(
                AnalyzeItemWorkflow.request_cancel
            )
        except Exception as exc:
            raise HTTPException(
                status_code=503, detail="Temporal cancellation is unavailable"
            ) from exc
        job.cancel_requested = True
    else:
        job.cancel_requested = True
        job.status = "cancelled"
        job.stage = "cancelled"
        job.completed_at = datetime.now(timezone.utc)
        item.processing_status = ProcessingStatus.SKIPPED
        item.analysis_status = AnalysisStatus.SKIPPED

    await _record_analysis_action(
        db,
        admin_id=admin.id,
        item_id=item.id,
        job_id=job.id,
        action="cancel",
        version=job.analysis_version,
        correlation_id=job.correlation_id,
    )
    await db.commit()
    updated = await _load_processing_job_context(db, job.id)
    assert updated is not None
    return _processing_job_response(*updated)


@router.post(
    "/items/{item_id}/reanalyze",
    response_model=AdminProcessingJobResponse,
    responses={**ERRORS, 409: {"model": ErrorResponse}},
)
async def reanalyze_admin_item(
    item_id: str,
    data: AdminAnalysisActionRequest,
    admin: CurrentAdmin,
    db: DbSession,
) -> AdminProcessingJobResponse:
    if data.confirmation != "REANALYZE":
        raise HTTPException(
            status_code=400, detail="REANALYZE confirmation is required"
        )
    item = await db.get(Item, item_id)
    if item is None:
        raise HTTPException(status_code=404, detail="Item not found")
    if item.deleted_at is not None:
        raise HTTPException(status_code=400, detail="Deleted items cannot be analyzed")
    active_job = await db.scalar(
        select(ProcessingJob).where(
            ProcessingJob.item_id == item.id,
            ProcessingJob.status.in_(("pending", "scheduled", "processing")),
        )
    )
    if active_job and active_job.reason == "admin_reanalyze":
        action_exists = await db.scalar(
            select(AdminAnalysisAction.id).where(
                AdminAnalysisAction.action == "reanalyze",
                AdminAnalysisAction.job_id == active_job.id,
            )
        )
        if action_exists:
            active_row = await _load_processing_job_context(db, active_job.id)
            assert active_row is not None
            return _processing_job_response(*active_row)
    prior_version = item.analysis_version
    previous_action = await db.scalar(
        select(AdminAnalysisAction).where(
            AdminAnalysisAction.idempotency_key
            == f"reanalyze:{item.id}:{prior_version}"
        )
    )
    if previous_action:
        existing = await db.scalar(
            select(ProcessingJob)
            .where(ProcessingJob.item_id == item.id)
            .order_by(ProcessingJob.analysis_version.desc())
        )
        if existing:
            existing_row = await _load_processing_job_context(db, existing.id)
            if existing_row:
                return _processing_job_response(*existing_row)
    try:
        job = await retry_item_analysis(
            db, item, reason="admin_reanalyze", settings=get_settings()
        )
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    await db.flush()
    await _record_analysis_action(
        db,
        admin_id=admin.id,
        item_id=item.id,
        job_id=job.id,
        action="reanalyze",
        version=prior_version,
        correlation_id=job.correlation_id,
    )
    job_id = job.id
    await db.commit()
    result = await _load_processing_job_context(db, job_id)
    assert result is not None
    return _processing_job_response(*result)


@router.patch("/users/{user_id}", response_model=AdminUserResponse, responses=ERRORS)
async def update_admin_user(
    user_id: str,
    data: AdminUserUpdate,
    admin: CurrentAdmin,
    db: DbSession,
) -> AdminUserResponse:
    user = await db.get(User, user_id)
    if user is None:
        raise HTTPException(status_code=404, detail="User not found")
    if user.id == admin.id and data.is_active is False:
        raise HTTPException(status_code=400, detail="Admins cannot disable themselves")
    if user.id == admin.id and data.role == UserRole.USER:
        raise HTTPException(status_code=400, detail="Admins cannot demote themselves")

    changes = data.model_dump(exclude_unset=True)
    if "role" in changes and changes["role"] is not None:
        user.role = changes["role"].value
    if "is_active" in changes and changes["is_active"] is not None:
        user.is_active = changes["is_active"]
    await db.commit()
    await db.refresh(user)
    return _admin_user_response(user)


@router.delete(
    "/users/{user_id}", status_code=status.HTTP_204_NO_CONTENT, responses=ERRORS
)
async def delete_admin_user(
    user_id: str,
    admin: CurrentAdmin,
    db: DbSession,
    storage: Storage,
) -> Response:
    user = await db.get(User, user_id)
    if user is None:
        raise HTTPException(status_code=404, detail="User not found")
    if user.id == admin.id:
        raise HTTPException(status_code=400, detail="Admins cannot delete themselves")
    await delete_user_account(
        db=db, storage=storage, user=user, event="admin_user_deleted"
    )
    return Response(status_code=204)
