"""Temporal activities for durable, independently retryable analysis stages."""

import hashlib
import logging
import time
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import selectinload
from temporalio import activity
from temporalio.exceptions import ApplicationError

from app.ai.audit import AIRunRecorder
from app.ai.budgets import DatabaseBudgetGuard
from app.ai.contracts import (
    AnalysisResult,
    chunk_document,
    enrichment_result_from_payload,
    enrichment_result_to_payload,
    extracted_document_from_payload,
    extracted_document_to_payload,
)
from app.ai.embedding_pipeline import EmbeddingPipeline, backfill_embeddings
from app.ai.factory import build_ai_gateway
from app.ai.gateway import ProviderError
from app.config import get_settings
from app.database import async_session_maker
from app.models import AnalysisStatus, Item, ProcessingJob, Tag, User
from app.observability import ACTIVITY_DURATION, ANALYSIS_OUTCOMES, SCHEDULE_TO_START
from app.services.analysis import (
    AnalysisOutcome,
    apply_processing_result,
    mark_analysis_failed,
    persist_enrichment_record,
    run_item_analysis,
)
from app.services.processing import ContentProcessor, fallback_summary, processing_input
from app.services.storage import get_storage_service
from app.temporal_pipeline.types import (
    AnalysisStageOutcome,
    AnalysisWorkflowInput,
    EmbeddingBackfillPageInput,
    EmbeddingBackfillPageOutcome,
)

logger = logging.getLogger(__name__)


def _heartbeat(*details: object) -> None:
    """Heartbeat in a worker while remaining directly unit-testable."""
    try:
        activity.heartbeat(*details)
    except RuntimeError:
        pass


def _record_activity(stage: str, started: float, outcome: str = "completed") -> None:
    ACTIVITY_DURATION.labels(stage, outcome).observe(time.perf_counter() - started)
    ANALYSIS_OUTCOMES.labels("temporal", stage, outcome).inc()


async def _load_item_and_job(
    request: AnalysisWorkflowInput,
) -> tuple[Item, ProcessingJob]:
    async with async_session_maker() as session:
        item = await session.scalar(
            select(Item)
            .options(selectinload(Item.assets))
            .where(Item.id == request.item_id, Item.deleted_at.is_(None))
        )
        job = await session.get(ProcessingJob, request.job_id)
        if item is None or job is None:
            raise ApplicationError(
                "Analysis item or job was not found", non_retryable=True
            )
        if item.analysis_version != request.analysis_version:
            raise ApplicationError("Analysis request is stale", non_retryable=True)
        if job.cancel_requested:
            raise ApplicationError(
                "Analysis cancellation requested", non_retryable=True
            )
        item._existing_tag_names = tuple(
            await session.scalars(select(Tag.name).where(Tag.user_id == item.user_id))
        )
        item._external_ai_allowed = bool(
            await session.scalar(
                select(User.ai_external_processing_allowed).where(
                    User.id == item.user_id
                )
            )
        )
        return item, job


async def _update_stage(
    request: AnalysisWorkflowInput,
    stage: str,
    *,
    stage_data: dict[str, object] | None = None,
    content_hash: str | None = None,
) -> None:
    async with async_session_maker() as session:
        job = await session.get(ProcessingJob, request.job_id)
        item = await session.get(Item, request.item_id)
        if (
            job is None
            or item is None
            or item.analysis_version != request.analysis_version
        ):
            raise ApplicationError("Analysis request is stale", non_retryable=True)
        now = datetime.now(timezone.utc)
        job.stage = stage
        job.updated_at = now
        if stage_data is not None:
            job.stage_data = stage_data
        if content_hash is not None:
            job.content_hash = content_hash
        if stage == "extracting":
            created_at = job.created_at
            if created_at.tzinfo is None:
                created_at = created_at.replace(tzinfo=timezone.utc)
            SCHEDULE_TO_START.labels("temporal").observe(
                max(0, (now - created_at).total_seconds())
            )
            job.status = "processing"
            job.attempts += 1
            job.locked_at = now
            item.analysis_status = AnalysisStatus.ANALYZING
            item.analysis_started_at = now
            item.analysis_error = None
        await session.commit()
        logger.info(
            "analysis stage updated",
            extra={
                "correlation_id": request.correlation_id,
                "job_id": request.job_id,
                "workflow_id": job.temporal_workflow_id,
                "provider": request.provider,
                "stage": stage,
            },
        )


@activity.defn
async def extract_item_activity(request: AnalysisWorkflowInput) -> AnalysisStageOutcome:
    started = time.perf_counter()
    item, job = await _load_item_and_job(request)
    existing = (job.stage_data or {}).get("extraction")
    if isinstance(existing, dict) and job.content_hash:
        _record_activity("extract", started, "checkpoint")
        return AnalysisStageOutcome(
            item.id, request.analysis_version, "extracted", job.content_hash
        )

    await _update_stage(request, "extracting")
    _heartbeat("extracting", request.item_id)
    settings = get_settings()
    processor = ContentProcessor(
        get_storage_service(),
        settings,
        budget_guard=DatabaseBudgetGuard(async_session_maker, settings),
        run_recorder=AIRunRecorder(async_session_maker),
    )
    document = await processor.extract(processing_input(item, job))
    _heartbeat("extracted", request.item_id)
    payload = extracted_document_to_payload(document)
    content_hash = hashlib.sha256(
        (document.normalized_text or document.extracted_text or "").encode("utf-8")
    ).hexdigest()
    data = dict(job.stage_data or {})
    data["extraction"] = payload
    await _update_stage(
        request, "extracted", stage_data=data, content_hash=content_hash
    )
    _record_activity("extract", started)
    return AnalysisStageOutcome(
        item.id, request.analysis_version, "extracted", content_hash
    )


@activity.defn
async def enrich_item_activity(request: AnalysisWorkflowInput) -> AnalysisStageOutcome:
    started = time.perf_counter()
    item, job = await _load_item_and_job(request)
    data = dict(job.stage_data or {})
    if isinstance(data.get("enrichment"), dict):
        _record_activity("enrich", started, "checkpoint")
        return AnalysisStageOutcome(
            item.id, request.analysis_version, "enriched", job.content_hash
        )
    extraction = data.get("extraction")
    if not isinstance(extraction, dict):
        raise ApplicationError("Extraction checkpoint is missing", non_retryable=True)

    await _update_stage(request, "enriching")
    settings = get_settings()
    processor = ContentProcessor(
        get_storage_service(),
        settings,
        budget_guard=DatabaseBudgetGuard(async_session_maker, settings),
        run_recorder=AIRunRecorder(async_session_maker),
    )
    document = extracted_document_from_payload(extraction)
    result = await processor.enrich(document, processing_input(item, job))
    data["enrichment"] = enrichment_result_to_payload(result)
    await _update_stage(request, "enriched", stage_data=data)
    _record_activity("enrich", started)
    return AnalysisStageOutcome(
        item.id, request.analysis_version, "enriched", job.content_hash
    )


@activity.defn
async def embed_item_activity(request: AnalysisWorkflowInput) -> AnalysisStageOutcome:
    started = time.perf_counter()
    item, job = await _load_item_and_job(request)
    data = dict(job.stage_data or {})
    if isinstance(data.get("chunks"), list):
        _record_activity("embed", started, "checkpoint")
        return AnalysisStageOutcome(
            item.id, request.analysis_version, "embedded", job.content_hash
        )
    extraction = data.get("extraction")
    if not isinstance(extraction, dict):
        raise ApplicationError("Extraction checkpoint is missing", non_retryable=True)

    await _update_stage(request, "embedding")
    document = extracted_document_from_payload(extraction)
    settings = get_settings()
    chunks = chunk_document(
        document,
        maximum_characters=settings.ai_embedding_chunk_characters,
        overlap=settings.ai_embedding_chunk_overlap,
    )
    for chunk in chunks:
        _heartbeat("embedding", chunk.ordinal, len(chunks))
    pipeline = EmbeddingPipeline(
        async_session_maker,
        build_ai_gateway(settings),
        settings,
        DatabaseBudgetGuard(async_session_maker, settings),
    )
    try:
        embedding_outcome = await pipeline.embed_document(
            document, user_id=item.user_id
        )
        data["embedding_index_id"] = embedding_outcome.index_id
        data["embedding_status"] = embedding_outcome.status
        data["embedded_chunks"] = embedding_outcome.embedded
        data["reused_chunks"] = embedding_outcome.reused
    except ProviderError as exc:
        data["embedding_status"] = f"degraded:{exc.code.value}"
    data["chunks"] = [
        {
            "chunk_id": chunk.chunk_id,
            "ordinal": chunk.ordinal,
            "start_offset": chunk.start_offset,
            "end_offset": chunk.end_offset,
            "content_hash": chunk.content_hash,
        }
        for chunk in chunks
    ]
    await _update_stage(request, "embedded", stage_data=data)
    _record_activity("embed", started)
    return AnalysisStageOutcome(
        item.id, request.analysis_version, "embedded", job.content_hash
    )


@activity.defn
async def backfill_embeddings_activity(
    request: EmbeddingBackfillPageInput,
) -> EmbeddingBackfillPageOutcome:
    """Embed one cursor page so Temporal can durably resume and rate-limit migration."""
    settings = get_settings()
    if not settings.ai_embedding_backfill_enabled:
        raise ApplicationError(
            "Embedding backfill is disabled by rollout policy",
            non_retryable=True,
        )
    if request.expected_index_version != settings.ai_embedding_index_version:
        raise ApplicationError(
            "Embedding index version does not match worker configuration",
            non_retryable=True,
        )
    page = await backfill_embeddings(
        EmbeddingPipeline(
            async_session_maker,
            build_ai_gateway(settings),
            settings,
            DatabaseBudgetGuard(async_session_maker, settings),
        ),
        cursor=request.cursor,
        limit=request.limit,
    )
    ANALYSIS_OUTCOMES.labels("temporal", "embedding_backfill", "completed").inc(
        len(page.outcomes)
    )
    _heartbeat("embedding_backfill", len(page.outcomes), page.next_cursor)
    return EmbeddingBackfillPageOutcome(
        processed=len(page.outcomes),
        next_cursor=page.next_cursor,
        exhausted=page.exhausted,
    )


@activity.defn
async def persist_analysis_activity(request: AnalysisWorkflowInput) -> AnalysisOutcome:
    started = time.perf_counter()
    item, job = await _load_item_and_job(request)
    if job.stage in {"persisted", "completed"}:
        _record_activity("persist", started, "checkpoint")
        return AnalysisOutcome(
            item_id=item.id,
            status=AnalysisStatus(item.analysis_status).value,
            analysis_version=item.analysis_version,
            summary_generated=bool(item.summary),
            extracted_text_length=len(item.extracted_text or ""),
        )
    data = dict(job.stage_data or {})
    extraction = data.get("extraction")
    enrichment = data.get("enrichment")
    if not isinstance(extraction, dict) or not isinstance(enrichment, dict):
        raise ApplicationError(
            "Analysis checkpoints are incomplete", non_retryable=True
        )

    await _update_stage(request, "persisting")
    document = extracted_document_from_payload(extraction)
    enrichment_result = enrichment_result_from_payload(enrichment)
    result = AnalysisResult.from_stages(
        document,
        enrichment_result,
        fallback_summary=fallback_summary(document.extracted_text or ""),
    )
    async with async_session_maker() as session:
        current = await session.get(Item, request.item_id)
        current_job = await session.get(ProcessingJob, request.job_id)
        if (
            current is None
            or current_job is None
            or current.analysis_version != request.analysis_version
        ):
            raise ApplicationError("Analysis request is stale", non_retryable=True)
        completed_at = datetime.now(timezone.utc)
        apply_processing_result(
            current, result, completed_at=completed_at, engine="temporal"
        )
        await persist_enrichment_record(
            session, current, result, completed_at=completed_at
        )
        current_job.stage = "persisted"
        current_job.updated_at = completed_at
        await session.commit()
        _record_activity("persist", started)
        return AnalysisOutcome(
            item_id=current.id,
            status=AnalysisStatus(current.analysis_status).value,
            analysis_version=current.analysis_version,
            summary_generated=bool(current.summary),
            extracted_text_length=len(current.extracted_text or ""),
        )


@activity.defn
async def index_item_activity(request: AnalysisWorkflowInput) -> AnalysisStageOutcome:
    started = time.perf_counter()
    item, job = await _load_item_and_job(request)
    now = datetime.now(timezone.utc)
    async with async_session_maker() as session:
        current_job = await session.get(ProcessingJob, request.job_id)
        if current_job is None:
            raise ApplicationError("Analysis job was not found", non_retryable=True)
        current_job.stage = "completed"
        current_job.status = "completed"
        current_job.locked_at = None
        current_job.completed_at = now
        current_job.updated_at = now
        await session.commit()
    _record_activity("index", started)
    return AnalysisStageOutcome(
        item.id, request.analysis_version, "completed", job.content_hash
    )


@activity.defn
async def analyze_item_activity(request: AnalysisWorkflowInput) -> AnalysisOutcome:
    """Compatibility activity for histories created before multistage-v1."""
    settings = get_settings()
    processor = ContentProcessor(
        get_storage_service(),
        settings,
        budget_guard=DatabaseBudgetGuard(async_session_maker, settings),
        run_recorder=AIRunRecorder(async_session_maker),
    )
    started = time.perf_counter()
    outcome = await run_item_analysis(
        async_session_maker,
        processor,
        request.item_id,
        request.analysis_version,
        job_id=request.job_id,
        engine="temporal",
        increment_job_attempt=True,
    )
    _record_activity("legacy_analyze", started, outcome.status)
    return outcome


@activity.defn
async def finalize_analysis_failure_activity(
    request: AnalysisWorkflowInput, error: str
) -> None:
    started = time.perf_counter()
    await mark_analysis_failed(
        async_session_maker,
        request.item_id,
        request.analysis_version,
        error,
        job_id=request.job_id,
        terminal=True,
    )
    _record_activity("finalize", started, "failed")


@activity.defn
async def finalize_analysis_cancellation_activity(
    request: AnalysisWorkflowInput,
) -> None:
    started = time.perf_counter()
    async with async_session_maker() as session:
        item = await session.get(Item, request.item_id)
        job = await session.get(ProcessingJob, request.job_id)
        if (
            item is None
            or job is None
            or item.analysis_version != request.analysis_version
        ):
            return
        now = datetime.now(timezone.utc)
        item.analysis_status = AnalysisStatus.PENDING
        item.analysis_error = "Analysis cancelled; retry is available"
        item.analysis_completed_at = None
        item.updated_at = now
        job.status = "cancelled"
        job.stage = "cancelled"
        job.locked_at = None
        job.last_error = item.analysis_error
        job.updated_at = now
        job.completed_at = now
        await session.commit()
    _record_activity("finalize", started, "cancelled")
