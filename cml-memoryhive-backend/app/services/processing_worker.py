"""Database-backed processing worker with crash recovery and retries."""

import logging
from datetime import datetime, timedelta, timezone

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker
from sqlalchemy.orm import selectinload

from app.ai.contracts import ExtractedDocument
from app.ai.embedding_pipeline import EmbeddingPipeline
from app.ai.gateway import ProviderError
from app.models import AnalysisStatus, Item, ProcessingJob, ProcessingStatus, Tag, User
from app.observability import (
    ANALYSIS_OUTCOMES,
    SCHEDULE_TO_START,
    WORKER_POLL_TOTAL,
    mark_worker_heartbeat,
    update_queue_metrics,
)
from app.services.analysis import apply_processing_result, persist_enrichment_record
from app.services.analysis_dispatch import (
    backfill_pending_analysis,
    retry_item_analysis,
)
from app.services.processing import ContentProcessor, ProcessingResult, processing_input

logger = logging.getLogger(__name__)


class ProcessingWorker:
    def __init__(
        self,
        session_factory: async_sessionmaker[AsyncSession],
        processor: ContentProcessor,
    ) -> None:
        self.session_factory = session_factory
        self.processor = processor

    async def claim(self) -> str | None:
        now = datetime.now(timezone.utc)
        stale = now - timedelta(minutes=10)
        async with self.session_factory() as session:
            await backfill_pending_analysis(session, limit=25)
            await session.execute(
                update(ProcessingJob)
                .where(
                    ProcessingJob.status == "processing",
                    ProcessingJob.locked_at < stale,
                )
                .values(status="pending", locked_at=None, next_attempt_at=now)
            )
            query = (
                select(ProcessingJob)
                .where(
                    ProcessingJob.execution_backend == "database",
                    ProcessingJob.status == "pending",
                    ProcessingJob.next_attempt_at <= now,
                )
                .order_by(ProcessingJob.created_at, ProcessingJob.id)
                .limit(1)
            )
            if session.bind and session.bind.dialect.name == "postgresql":
                query = query.with_for_update(skip_locked=True)
            job = await session.scalar(query)
            if job is None:
                await session.commit()
                return None
            job.status = "processing"
            created_at = job.created_at
            if created_at.tzinfo is None:
                created_at = created_at.replace(tzinfo=timezone.utc)
            SCHEDULE_TO_START.labels("database").observe(
                max(0, (now - created_at).total_seconds())
            )
            job.attempts += 1
            job.locked_at = now
            job.updated_at = now
            item = await session.get(Item, job.item_id)
            if item and (
                job.analysis_version is None
                or job.analysis_version == item.analysis_version
            ):
                item.processing_status = ProcessingStatus.PROCESSING
                item.processing_error = None
                item.analysis_status = AnalysisStatus.ANALYZING
                item.analysis_started_at = now
                item.analysis_error = None
            await session.commit()
            return job.id

    async def run_once(self) -> bool:
        mark_worker_heartbeat("database_worker")
        await update_queue_metrics(self.session_factory, backend="database")
        job_id = await self.claim()
        if job_id is None:
            WORKER_POLL_TOTAL.labels("database_worker", "idle").inc()
            return False
        WORKER_POLL_TOTAL.labels("database_worker", "claimed").inc()
        try:
            async with self.session_factory() as session:
                job = await session.get(ProcessingJob, job_id)
                item = await session.scalar(
                    select(Item)
                    .options(selectinload(Item.assets))
                    .where(Item.id == job.item_id if job else "")
                )
                if job is None or item is None or item.deleted_at is not None:
                    await self._complete(job_id, ProcessingResult())
                    return True
                if (
                    job.analysis_version is not None
                    and job.analysis_version != item.analysis_version
                ):
                    await self._skip(job_id, "Analysis request is stale")
                    return True
                item._existing_tag_names = tuple(
                    await session.scalars(
                        select(Tag.name).where(Tag.user_id == item.user_id)
                    )
                )
                item._external_ai_allowed = bool(
                    await session.scalar(
                        select(User.ai_external_processing_allowed).where(
                            User.id == item.user_id
                        )
                    )
                )
                value = processing_input(item, job)
            result = await self.processor.process(value)
            await self._complete(job_id, result)
            gateway = getattr(self.processor, "ai_gateway", None)
            processor_settings = getattr(self.processor, "settings", None)
            if gateway is not None and processor_settings is not None:
                try:
                    await EmbeddingPipeline(
                        self.session_factory,
                        gateway,
                        processor_settings,
                        getattr(self.processor, "budget_guard", None),
                    ).embed_document(
                        ExtractedDocument(
                            item_id=value.item_id,
                            analysis_version=value.analysis_version,
                            extracted_text=result.extracted_text,
                            normalized_text=result.normalized_text,
                            language=result.language,
                        ),
                        user_id=value.user_id or "",
                    )
                except ProviderError as exc:
                    logger.warning(
                        "Optional embedding failed: provider=%s code=%s",
                        exc.provider.value,
                        exc.code.value,
                    )
            outcome = "degraded" if result.enrichment_errors else "completed"
            ANALYSIS_OUTCOMES.labels("database", "completed", outcome).inc()
        except Exception as exc:
            logger.exception("Processing job %s failed", job_id)
            await self._fail(job_id, str(exc))
            ANALYSIS_OUTCOMES.labels("database", "processing", "failed").inc()
        return True

    async def _complete(self, job_id: str, result: ProcessingResult) -> None:
        now = datetime.now(timezone.utc)
        async with self.session_factory() as session:
            job = await session.get(ProcessingJob, job_id)
            if job is None:
                return
            item = await session.get(Item, job.item_id)
            if item and item.deleted_at is None:
                if (
                    job.analysis_version is None
                    or job.analysis_version == item.analysis_version
                ):
                    apply_processing_result(
                        item,
                        result,
                        completed_at=now,
                        engine="processing_worker",
                    )
                    await persist_enrichment_record(
                        session, item, result, completed_at=now
                    )
                    attribution = (item.item_metadata or {}).get("summary_attribution", "Summary updated")
                    logger.info("Item %s: %s", item.id, attribution)
            job.status = "completed"
            job.locked_at = None
            job.last_error = None
            job.updated_at = now
            job.completed_at = now
            await session.commit()

    async def _skip(self, job_id: str, message: str) -> None:
        now = datetime.now(timezone.utc)
        async with self.session_factory() as session:
            job = await session.get(ProcessingJob, job_id)
            if job is None:
                return
            job.status = "skipped"
            job.locked_at = None
            job.last_error = message
            job.updated_at = now
            job.completed_at = now
            await session.commit()

    async def _fail(self, job_id: str, error: str) -> None:
        now = datetime.now(timezone.utc)
        async with self.session_factory() as session:
            job = await session.get(ProcessingJob, job_id)
            if job is None:
                return
            exhausted = job.attempts >= job.max_attempts
            job.status = "failed" if exhausted else "pending"
            job.locked_at = None
            job.last_error = error[:4000]
            job.updated_at = now
            job.next_attempt_at = now + timedelta(seconds=min(300, 2**job.attempts))
            item = await session.get(Item, job.item_id)
            if item and item.deleted_at is None:
                if (
                    job.analysis_version is not None
                    and job.analysis_version != item.analysis_version
                ):
                    job.status = "skipped"
                    job.locked_at = None
                    job.last_error = "Analysis request is stale"
                    job.updated_at = now
                    job.completed_at = now
                    await session.commit()
                    return
                item.processing_status = (
                    ProcessingStatus.FAILED if exhausted else ProcessingStatus.PENDING
                )
                item.processing_error = job.last_error
                item.analysis_status = (
                    AnalysisStatus.FAILED if exhausted else AnalysisStatus.PENDING
                )
                item.analysis_error = job.last_error
                item.analysis_completed_at = now if exhausted else None
                item.updated_at = now
            await session.commit()


async def retry_failed_item(session: AsyncSession, item: Item) -> ProcessingJob:
    """Backward-compatible entry point for existing callers and tests."""
    return await retry_item_analysis(session, item)
