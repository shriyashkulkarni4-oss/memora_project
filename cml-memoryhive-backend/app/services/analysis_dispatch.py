"""Transactional scheduling intent for every item-analysis entry point."""

import uuid
from dataclasses import dataclass
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.factory import build_ai_gateway
from app.ai.policy import AITask, resolve_task_policy
from app.config import Settings, get_settings
from app.middleware.runtime import current_request_id
from app.models import (
    AnalysisExecutionBackend,
    AnalysisStatus,
    Item,
    ItemType,
    ProcessingJob,
    ProcessingStatus,
)
from app.observability import DISPATCH_TOTAL, safe_reason

ACTIVE_JOB_STATUSES = ("pending", "scheduled", "processing")


@dataclass(frozen=True)
class AnalysisDispatchDecision:
    job: ProcessingJob
    created: bool


def configured_backend(settings: Settings | None = None) -> AnalysisExecutionBackend:
    resolved = settings or get_settings()
    return (
        AnalysisExecutionBackend.TEMPORAL
        if resolved.temporal_enabled
        else AnalysisExecutionBackend.DATABASE
    )


def mark_analysis_pending(item: Item, requested_at: datetime) -> None:
    item.analysis_status = AnalysisStatus.PENDING
    item.analysis_error = None
    item.analysis_requested_at = requested_at
    item.analysis_started_at = None
    item.analysis_completed_at = None
    if ItemType(item.type) == ItemType.TEXT:
        item.processing_status = ProcessingStatus.READY
        item.processing_error = None
    else:
        item.processing_status = ProcessingStatus.PENDING
        item.processing_error = None


async def request_item_analysis(
    session: AsyncSession,
    item: Item,
    *,
    reason: str,
    settings: Settings | None = None,
    increment_version: bool = False,
    requested_at: datetime | None = None,
    correlation_id: str | None = None,
) -> AnalysisDispatchDecision:
    """Persist item state and exactly one dispatch intent for its version."""
    now = requested_at or datetime.now(timezone.utc)
    if increment_version:
        item.analysis_version += 1

    existing = await session.scalar(
        select(ProcessingJob).where(
            ProcessingJob.item_id == item.id,
            ProcessingJob.analysis_version == item.analysis_version,
        )
    )
    if existing is not None:
        DISPATCH_TOTAL.labels(
            existing.execution_backend, safe_reason(reason), "reused"
        ).inc()
        return AnalysisDispatchDecision(job=existing, created=False)

    mark_analysis_pending(item, now)
    item.updated_at = now
    resolved_settings = settings or get_settings()
    decision = resolve_task_policy(
        resolved_settings, build_ai_gateway(resolved_settings), AITask.ENRICHMENT
    )
    job = ProcessingJob(
        item_id=item.id,
        kind=ItemType(item.type).value,
        analysis_version=item.analysis_version,
        execution_backend=configured_backend(settings).value,
        reason=reason,
        correlation_id=correlation_id or current_request_id() or str(uuid.uuid4()),
        ai_provider=(decision.primary.provider.value if decision.primary else None),
        ai_model=decision.primary.model if decision.primary else None,
        ai_policy=decision.to_payload(),
        next_attempt_at=now,
        created_at=now,
        updated_at=now,
    )
    session.add(job)
    DISPATCH_TOTAL.labels(job.execution_backend, safe_reason(reason), "created").inc()
    return AnalysisDispatchDecision(job=job, created=True)


async def retry_item_analysis(
    session: AsyncSession,
    item: Item,
    *,
    reason: str = "manual_retry",
    settings: Settings | None = None,
) -> ProcessingJob:
    active = await session.scalar(
        select(ProcessingJob.id).where(
            ProcessingJob.item_id == item.id,
            ProcessingJob.status.in_(ACTIVE_JOB_STATUSES),
        )
    )
    if active:
        raise ValueError("Item processing is already queued")
    decision = await request_item_analysis(
        session,
        item,
        reason=reason,
        settings=settings,
        increment_version=True,
    )
    return decision.job


async def backfill_pending_analysis(
    session: AsyncSession,
    *,
    limit: int,
    settings: Settings | None = None,
) -> list[ProcessingJob]:
    """Repair pending items that have no durable dispatch record."""
    candidates = list(
        (
            await session.scalars(
                select(Item)
                .where(
                    Item.deleted_at.is_(None),
                    Item.analysis_status == AnalysisStatus.PENDING.value,
                    ~Item.processing_jobs.any(
                        ProcessingJob.status.in_(ACTIVE_JOB_STATUSES)
                    ),
                )
                .order_by(
                    Item.analysis_requested_at.asc().nullsfirst(),
                    Item.created_at.asc(),
                    Item.id.asc(),
                )
                .limit(limit)
            )
        ).all()
    )
    jobs: list[ProcessingJob] = []
    for item in candidates:
        decision = await request_item_analysis(
            session,
            item,
            reason="backfill",
            settings=settings,
        )
        if decision.created:
            jobs.append(decision.job)
    return jobs
