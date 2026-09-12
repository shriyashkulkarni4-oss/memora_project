"""Regression coverage for transactional item-analysis dispatch."""

from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest
from httpx import AsyncClient
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.api.v1 import items as items_api
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
from app.services.analysis import apply_processing_result
from app.services.analysis_dispatch import (
    backfill_pending_analysis,
    request_item_analysis,
)
from app.services.processing import ProcessingResult
from app.services.processing_worker import ProcessingWorker
from app.temporal_pipeline import scheduler
from tests.conftest import FakeStorage
from tests.test_core_api import PNG_1X1, register_and_login

pytestmark = pytest.mark.asyncio


class SuccessfulTextProcessor:
    async def process(self, _value: object) -> ProcessingResult:
        return ProcessingResult(
            extracted_text="Text also executes on the database worker.",
            normalized_text="text also executes on the database worker.",
            summary="Text analysis completed.",
        )


class FakeTemporalClient:
    def __init__(self) -> None:
        self.started: list[tuple[object, str, str]] = []

    async def start_workflow(
        self,
        _workflow: object,
        request: object,
        *,
        id: str,
        task_queue: str,
        **_kwargs: object,
    ) -> None:
        self.started.append((request, id, task_queue))


class FakeWorkflowHandle:
    def __init__(self) -> None:
        self.signals: list[object] = []

    async def signal(self, signal: object) -> None:
        self.signals.append(signal)


class FakeControlClient:
    def __init__(self, handle: FakeWorkflowHandle) -> None:
        self.handle = handle
        self.workflow_ids: list[str] = []

    def get_workflow_handle(self, workflow_id: str) -> FakeWorkflowHandle:
        self.workflow_ids.append(workflow_id)
        return self.handle


async def dispatch_database(tmp_path: Path):
    engine = create_async_engine(f"sqlite+aiosqlite:///{tmp_path / 'dispatch.db'}")
    factory = async_sessionmaker(engine, expire_on_commit=False)
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
    return engine, factory


async def test_dispatch_is_idempotent_and_backend_is_fixed_for_version(
    tmp_path: Path,
) -> None:
    engine, factory = await dispatch_database(tmp_path)
    async with factory() as session:
        user = User(email="dispatch@example.com", hashed_password="hash")
        item = Item(
            user=user,
            type=ItemType.TEXT,
            raw_text="Analyze this text capture.",
            processing_status=ProcessingStatus.READY,
        )
        session.add(item)
        first = await request_item_analysis(
            session,
            item,
            reason="capture",
            settings=Settings(
                database_url="sqlite+aiosqlite://", temporal_enabled=True
            ),
        )
        duplicate = await request_item_analysis(
            session,
            item,
            reason="capture",
            settings=Settings(
                database_url="sqlite+aiosqlite://", temporal_enabled=False
            ),
        )
        await session.commit()

        assert first.created is True
        assert duplicate.created is False
        assert duplicate.job.id == first.job.id
        assert first.job.execution_backend == "temporal"
        assert item.analysis_status == AnalysisStatus.PENDING
        assert item.processing_status == ProcessingStatus.READY
        assert (
            await session.scalar(select(func.count()).select_from(ProcessingJob)) == 1
        )
    await engine.dispose()


async def test_dispatch_captures_immutable_ai_route_and_fallback_policy(
    tmp_path: Path,
) -> None:
    engine, factory = await dispatch_database(tmp_path)
    settings = Settings(
        database_url="sqlite+aiosqlite://",
        ollama_base_url="http://ollama:11434",
        n8n_webhook_url="http://n8n:5678/enrich",
        ai_enrichment_route="ollama:qwen-route",
        ai_enrichment_fallback_routes=["n8n"],
        ai_cross_provider_fallback_enabled=True,
    )
    async with factory() as session:
        user = User(email="policy@example.com", hashed_password="hash")
        item = Item(
            user=user,
            type=ItemType.TEXT,
            raw_text="Capture the selected route with the job.",
            processing_status=ProcessingStatus.READY,
        )
        session.add(item)
        decision = await request_item_analysis(
            session, item, reason="capture", settings=settings
        )
        await session.commit()

        assert decision.job.ai_provider == "ollama"
        assert decision.job.ai_model == "qwen-route"
        assert decision.job.ai_policy["fallbacks"] == [
            {"provider": "n8n", "model": None, "external": False}
        ]

        changed = settings.model_copy(
            update={"ai_enrichment_route": None, "ai_enrichment_fallback_routes": []}
        )
        assert changed.ai_enrichment_route is None
        persisted = await session.get(ProcessingJob, decision.job.id)
        assert persisted is not None
        assert persisted.ai_provider == "ollama"
        assert persisted.ai_policy["fallbacks"][0]["provider"] == "n8n"
    await engine.dispose()


async def test_backfill_repairs_pending_item_without_dispatch(tmp_path: Path) -> None:
    engine, factory = await dispatch_database(tmp_path)
    async with factory() as session:
        user = User(email="backfill@example.com", hashed_password="hash")
        item = Item(
            user=user,
            type=ItemType.TEXT,
            raw_text="Orphaned pending analysis.",
            processing_status=ProcessingStatus.READY,
            analysis_status=AnalysisStatus.PENDING,
        )
        session.add(item)
        await session.commit()

        jobs = await backfill_pending_analysis(
            session,
            limit=10,
            settings=Settings(database_url="sqlite+aiosqlite://"),
        )
        await session.commit()

        assert len(jobs) == 1
        assert jobs[0].item_id == item.id
        assert jobs[0].analysis_version == item.analysis_version
        assert jobs[0].reason == "backfill"
        assert jobs[0].execution_backend == "database"
    await engine.dispose()


async def test_database_worker_executes_text_and_recovers_stale_claim(
    tmp_path: Path,
) -> None:
    engine, factory = await dispatch_database(tmp_path)
    async with factory() as session:
        user = User(email="worker-text@example.com", hashed_password="hash")
        item = Item(
            user=user,
            type=ItemType.TEXT,
            raw_text="Text also executes on the database worker.",
            processing_status=ProcessingStatus.READY,
        )
        session.add(item)
        decision = await request_item_analysis(session, item, reason="capture")
        await session.commit()
        decision.job.status = "processing"
        decision.job.locked_at = datetime.now(timezone.utc) - timedelta(minutes=11)
        await session.commit()

    worker = ProcessingWorker(factory, SuccessfulTextProcessor())  # type: ignore[arg-type]
    assert await worker.run_once() is True

    async with factory() as session:
        persisted = await session.get(Item, item.id)
        job = await session.get(ProcessingJob, decision.job.id)
        assert persisted and persisted.analysis_status == AnalysisStatus.ANALYZED
        assert persisted.summary == "Text analysis completed."
        assert persisted.processing_status == ProcessingStatus.READY
        assert job and job.status == "completed"
    await engine.dispose()


async def test_temporal_scheduler_uses_outbox_and_marks_item_scheduled(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    engine, factory = await dispatch_database(tmp_path)
    temporal_settings = Settings(
        database_url="sqlite+aiosqlite://",
        temporal_enabled=True,
        temporal_task_queue="test-analysis",
    )
    async with factory() as session:
        user = User(email="temporal@example.com", hashed_password="hash")
        item = Item(
            user=user,
            type=ItemType.TEXT,
            raw_text="Schedule this through Temporal.",
            processing_status=ProcessingStatus.READY,
        )
        session.add(item)
        decision = await request_item_analysis(
            session, item, reason="capture", settings=temporal_settings
        )
        await session.commit()
        item_id = item.id
        job_id = decision.job.id

    monkeypatch.setattr(scheduler, "async_session_maker", factory)
    monkeypatch.setattr(scheduler, "get_settings", lambda: temporal_settings)
    client = FakeTemporalClient()
    started = await scheduler.start_pending_workflows(client, 10)  # type: ignore[arg-type]

    assert started == 1
    assert len(client.started) == 1
    request, workflow_id, task_queue = client.started[0]
    assert request.job_id == job_id  # type: ignore[attr-defined]
    assert workflow_id == f"memoryhive-analysis-{item_id}-v1"
    assert task_queue == "test-analysis"
    async with factory() as session:
        persisted = await session.get(Item, item_id)
        job = await session.get(ProcessingJob, job_id)
        assert persisted and persisted.analysis_status == AnalysisStatus.SCHEDULED
        assert job and job.status == "scheduled"
        assert job.temporal_workflow_id == workflow_id
    await engine.dispose()


async def test_owner_can_request_safe_temporal_cancellation(
    api_client_with_db: tuple[
        AsyncClient, FakeStorage, async_sessionmaker[AsyncSession]
    ],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    client, _storage, factory = api_client_with_db
    _user, headers = await register_and_login(client, "cancel-owner@example.com")
    created = await client.post(
        "/api/v1/items",
        json={"type": "text", "raw_text": "Cancel this analysis."},
        headers=headers,
    )
    assert created.status_code == 201
    item_id = created.json()["id"]
    async with factory() as session:
        job = await session.scalar(
            select(ProcessingJob).where(ProcessingJob.item_id == item_id)
        )
        assert job
        job.execution_backend = "temporal"
        job.status = "scheduled"
        job.temporal_workflow_id = "workflow-cancel-test"
        await session.commit()
        job_id = job.id

    handle = FakeWorkflowHandle()
    temporal_client = FakeControlClient(handle)

    async def connect(*_args: object, **_kwargs: object) -> FakeControlClient:
        return temporal_client

    monkeypatch.setattr(items_api.Client, "connect", connect)
    response = await client.post(
        f"/api/v1/items/{item_id}/analysis/cancel", headers=headers
    )

    assert response.status_code == 200, response.text
    assert response.json()["error"] == "Analysis cancellation requested"
    assert temporal_client.workflow_ids == ["workflow-cancel-test"]
    assert len(handle.signals) == 1
    async with factory() as session:
        job = await session.get(ProcessingJob, job_id)
        assert job and job.cancel_requested is True


async def test_api_dispatches_every_type_and_only_content_edits_create_versions(
    api_client_with_db: tuple[
        AsyncClient, FakeStorage, async_sessionmaker[AsyncSession]
    ],
) -> None:
    client, _storage, factory = api_client_with_db
    _user, headers = await register_and_login(client, "all-types@example.com")

    link = await client.post(
        "/api/v1/items",
        json={"type": "link", "url": "https://example.com/dispatch"},
        headers=headers,
    )
    text = await client.post(
        "/api/v1/items",
        json={"type": "text", "raw_text": "Text also gets analysis work."},
        headers=headers,
    )
    screenshot = await client.post(
        "/api/v1/items/screenshot",
        files={"file": ("dispatch.png", PNG_1X1, "image/png")},
        headers=headers,
    )
    assert link.status_code == 201
    assert text.status_code == 201
    assert screenshot.status_code == 201

    item_id = text.json()["id"]
    favorite = await client.put(f"/api/v1/items/{item_id}/favorite", headers=headers)
    assert favorite.status_code == 200
    updated = await client.patch(
        f"/api/v1/items/{item_id}",
        json={
            "expected_revision": favorite.json()["revision"],
            "raw_text": "Updated text creates a new version.",
        },
        headers=headers,
    )
    assert updated.status_code == 200
    assert updated.json()["analysis_version"] == 2

    async with factory() as session:
        jobs = list(
            (
                await session.scalars(
                    select(ProcessingJob).order_by(
                        ProcessingJob.item_id, ProcessingJob.analysis_version
                    )
                )
            ).all()
        )
        assert len(jobs) == 4
        text_jobs = [job for job in jobs if job.item_id == item_id]
        assert [job.analysis_version for job in text_jobs] == [1, 2]
        assert {job.kind for job in jobs} == {"link", "text", "screenshot"}


async def test_configured_ai_failure_is_recorded_as_degraded() -> None:
    item = Item(
        id="degraded-item",
        user_id="user-id",
        type=ItemType.TEXT,
        raw_text="Content remains useful when optional AI fails.",
        processing_status=ProcessingStatus.READY,
        revision=1,
        analysis_version=1,
    )
    result = ProcessingResult(
        extracted_text=item.raw_text,
        normalized_text=item.raw_text.casefold(),
        summary=item.raw_text,
        enrichment_attempted=True,
        enrichment_errors=["ollama_unavailable"],
    )

    apply_processing_result(
        item,
        result,
        completed_at=datetime.now(timezone.utc),
        engine="processing_worker",
    )

    assert item.analysis_status == AnalysisStatus.DEGRADED
    assert item.analysis_error == "ollama_unavailable"
    assert item.processing_status == ProcessingStatus.READY
    assert item.item_metadata and item.item_metadata["analysis"]["degraded"] is True
