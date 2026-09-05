"""Database-backed processing worker with crash recovery and retries."""

import logging
from datetime import datetime, timedelta, timezone

from sqlalchemy import or_, select, update
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker
from sqlalchemy.orm import selectinload

from app.models import Item, ItemType, ProcessingJob, ProcessingStatus
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
            job.attempts += 1
            job.locked_at = now
            job.updated_at = now
            item = await session.get(Item, job.item_id)
            if item:
                item.processing_status = ProcessingStatus.PROCESSING
                item.processing_error = None
            await session.commit()
            return job.id

    async def run_once(self) -> bool:
        job_id = await self.claim()
        if job_id is None:
            return False
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
                value = processing_input(item)
            result = await self.processor.process(value)
            await self._complete(job_id, result)
        except Exception as exc:
            logger.exception("Processing job %s failed", job_id)
            await self._fail(job_id, str(exc))
        return True

    async def _complete(self, job_id: str, result: ProcessingResult) -> None:
        now = datetime.now(timezone.utc)
        async with self.session_factory() as session:
            job = await session.get(ProcessingJob, job_id)
            if job is None:
                return
            item = await session.get(Item, job.item_id)
            if item and item.deleted_at is None:
                for field in (
                    "title",
                    "description",
                    "author",
                    "published_at",
                    "favicon_url",
                    "extracted_text",
                    "normalized_text",
                    "language",
                    "summary",
                ):
                    value = getattr(result, field)
                    preserves_user_value = field in {"title", "description"}
                    if value is not None and (
                        not preserves_user_value or getattr(item, field) is None
                    ):
                        setattr(item, field, value)
                item.item_metadata = {**(item.item_metadata or {}), **result.metadata}
                item.processing_status = ProcessingStatus.READY
                item.processing_error = None
                item.revision += 1
                item.updated_at = now
            job.status = "completed"
            job.locked_at = None
            job.last_error = None
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
                item.processing_status = (
                    ProcessingStatus.FAILED if exhausted else ProcessingStatus.PENDING
                )
                item.processing_error = job.last_error
                item.updated_at = now
            await session.commit()


async def retry_failed_item(session: AsyncSession, item: Item) -> ProcessingJob:
    active = await session.scalar(
        select(ProcessingJob.id).where(
            ProcessingJob.item_id == item.id,
            or_(
                ProcessingJob.status == "pending", ProcessingJob.status == "processing"
            ),
        )
    )
    if active:
        raise ValueError("Item processing is already queued")
    job = ProcessingJob(item_id=item.id, kind=ItemType(item.type).value)
    session.add(job)
    item.processing_status = ProcessingStatus.PENDING
    item.processing_error = None
    item.updated_at = datetime.now(timezone.utc)
    return job
