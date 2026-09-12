"""Durable Temporal stage checkpoint regression tests."""

from pathlib import Path

import pytest
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from temporalio.exceptions import ApplicationError

from app.config import Settings
from app.database import Base
from app.models import (
    AnalysisStatus,
    Item,
    ItemType,
    ProcessingJob,
    ProcessingStatus,
    User,
)
from app.temporal_pipeline import activities
from app.temporal_pipeline.types import AnalysisWorkflowInput

pytestmark = [pytest.mark.asyncio, pytest.mark.integration]


class UnusedStorage:
    pass


async def temporal_database(tmp_path: Path):
    engine = create_async_engine(f"sqlite+aiosqlite:///{tmp_path / 'stages.db'}")
    factory = async_sessionmaker(engine, expire_on_commit=False)
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
    async with factory() as session:
        user = User(email="stages@example.com", hashed_password="hash")
        item = Item(
            user=user,
            type=ItemType.TEXT,
            raw_text="Temporal stages preserve this extracted content.",
            processing_status=ProcessingStatus.READY,
            analysis_status=AnalysisStatus.SCHEDULED,
        )
        session.add(item)
        await session.flush()
        job = ProcessingJob(
            item_id=item.id,
            kind=ItemType.TEXT.value,
            analysis_version=1,
            execution_backend="temporal",
            status="scheduled",
        )
        session.add(job)
        await session.commit()
        request = AnalysisWorkflowInput(job.id, item.id, 1, item_type="text")
    return engine, factory, request


async def test_stages_checkpoint_and_resume_without_repeating_extraction(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    engine, factory, request = await temporal_database(tmp_path)
    monkeypatch.setattr(activities, "async_session_maker", factory)
    monkeypatch.setattr(activities, "get_storage_service", lambda: UnusedStorage())
    monkeypatch.setattr(
        activities,
        "get_settings",
        lambda: Settings(database_url="sqlite+aiosqlite://"),
    )

    first = await activities.extract_item_activity(request)
    second = await activities.extract_item_activity(request)
    assert first == second

    await activities.enrich_item_activity(request)
    await activities.embed_item_activity(request)
    outcome = await activities.persist_analysis_activity(request)
    repeated_outcome = await activities.persist_analysis_activity(request)
    indexed = await activities.index_item_activity(request)

    assert outcome.status == AnalysisStatus.ANALYZED.value
    assert repeated_outcome == outcome
    assert indexed.stage == "completed"
    async with factory() as session:
        item = await session.get(Item, request.item_id)
        job = await session.get(ProcessingJob, request.job_id)
        assert item and item.summary
        assert item.revision == 2
        assert item.analysis_status == AnalysisStatus.ANALYZED
        assert job and job.status == "completed"
        assert job.stage == "completed"
        assert job.attempts == 1
        assert job.content_hash
        assert job.stage_data["extraction"]["extracted_text"].startswith(
            "Temporal stages"
        )
        assert isinstance(job.stage_data["chunks"], list)
    await engine.dispose()


async def test_stale_stage_is_non_retryable(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    engine, factory, request = await temporal_database(tmp_path)
    monkeypatch.setattr(activities, "async_session_maker", factory)
    stale = AnalysisWorkflowInput(request.job_id, request.item_id, 2)

    with pytest.raises(ApplicationError) as caught:
        await activities.extract_item_activity(stale)
    assert caught.value.non_retryable is True
    await engine.dispose()


async def test_cancellation_leaves_recoverable_item_state(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    engine, factory, request = await temporal_database(tmp_path)
    monkeypatch.setattr(activities, "async_session_maker", factory)

    await activities.finalize_analysis_cancellation_activity(request)

    async with factory() as session:
        item = await session.get(Item, request.item_id)
        job = await session.get(ProcessingJob, request.job_id)
        assert item and item.analysis_status == AnalysisStatus.PENDING
        assert item.analysis_completed_at is None
        assert job and job.status == "cancelled"
        assert job.stage == "cancelled"
    await engine.dispose()
