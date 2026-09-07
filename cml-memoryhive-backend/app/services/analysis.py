"""Durable item analysis helpers shared by Temporal activities and tests."""

from dataclasses import dataclass
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker
from sqlalchemy.orm import selectinload

from app.models import AnalysisStatus, Item, ItemType, ProcessingStatus
from app.services.processing import ContentProcessor, ProcessingResult, processing_input


@dataclass(frozen=True)
class AnalysisOutcome:
    item_id: str
    status: str
    analysis_version: int
    summary_generated: bool = False
    extracted_text_length: int = 0
    message: str | None = None


def apply_processing_result(
    item: Item, result: ProcessingResult, *, completed_at: datetime
) -> None:
    """Apply extracted content while preserving user-entered title/description."""
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
    item.item_metadata = {
        **(item.item_metadata or {}),
        **result.metadata,
        "analysis": {
            "engine": "temporal",
            "version": item.analysis_version,
            "completed_at": completed_at.isoformat(),
        },
    }
    item.analysis_status = AnalysisStatus.ANALYZED
    item.analysis_error = None
    item.analysis_completed_at = completed_at
    item.processing_status = ProcessingStatus.READY
    item.processing_error = None
    item.revision += 1
    item.updated_at = completed_at


async def _load_item(session: AsyncSession, item_id: str) -> Item | None:
    return await session.scalar(
        select(Item)
        .options(selectinload(Item.assets))
        .where(Item.id == item_id, Item.deleted_at.is_(None))
    )


async def run_item_analysis(
    session_factory: async_sessionmaker[AsyncSession],
    processor: ContentProcessor,
    item_id: str,
    analysis_version: int | None = None,
) -> AnalysisOutcome:
    """Analyze one item idempotently for the requested analysis version."""
    async with session_factory() as session:
        item = await _load_item(session, item_id)
        if item is None:
            return AnalysisOutcome(
                item_id, AnalysisStatus.SKIPPED.value, 0, message="Item not found"
            )
        if analysis_version is not None and item.analysis_version != analysis_version:
            return AnalysisOutcome(
                item_id,
                AnalysisStatus.SKIPPED.value,
                item.analysis_version,
                message="Analysis request is stale",
            )
        item.analysis_status = AnalysisStatus.ANALYZING
        item.analysis_started_at = datetime.now(timezone.utc)
        item.analysis_error = None
        if ItemType(item.type) != ItemType.TEXT:
            item.processing_status = ProcessingStatus.PROCESSING
            item.processing_error = None
        payload = processing_input(item)
        await session.commit()

    try:
        result = await processor.process(payload)
    except Exception as exc:
        await mark_analysis_failed(session_factory, item_id, analysis_version, str(exc))
        raise

    completed_at = datetime.now(timezone.utc)
    async with session_factory() as session:
        item = await _load_item(session, item_id)
        if item is None:
            return AnalysisOutcome(
                item_id, AnalysisStatus.SKIPPED.value, 0, message="Item not found"
            )
        if analysis_version is not None and item.analysis_version != analysis_version:
            return AnalysisOutcome(
                item_id,
                AnalysisStatus.SKIPPED.value,
                item.analysis_version,
                message="Analysis request is stale",
            )
        apply_processing_result(item, result, completed_at=completed_at)
        await session.commit()
        return AnalysisOutcome(
            item_id=item.id,
            status=AnalysisStatus.ANALYZED.value,
            analysis_version=item.analysis_version,
            summary_generated=bool(item.summary),
            extracted_text_length=len(item.extracted_text or ""),
        )


async def mark_analysis_failed(
    session_factory: async_sessionmaker[AsyncSession],
    item_id: str,
    analysis_version: int | None,
    error: str,
) -> None:
    async with session_factory() as session:
        item = await _load_item(session, item_id)
        if item is None:
            return
        if analysis_version is not None and item.analysis_version != analysis_version:
            return
        now = datetime.now(timezone.utc)
        item.analysis_status = AnalysisStatus.FAILED
        item.analysis_error = error[:4000]
        item.analysis_completed_at = now
        if ItemType(item.type) != ItemType.TEXT:
            item.processing_status = ProcessingStatus.FAILED
            item.processing_error = item.analysis_error
        item.updated_at = now
        await session.commit()
