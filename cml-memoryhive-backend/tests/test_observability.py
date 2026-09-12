"""Bounded metrics and correlation propagation tests."""

import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

import httpx
import pytest
from prometheus_client import generate_latest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.ai.contracts import ExtractionInput
from app.config import Settings
from app.database import Base
from app.models import Item, ItemType, ProcessingJob, ProcessingStatus, User
from app.observability import (
    WORKER_HEARTBEAT,
    configured_model_alias,
    mark_worker_heartbeat,
    update_queue_metrics,
)
from app.services.processing import ContentProcessor
from tests.conftest import FakeStorage
from tests.test_core_api import register_and_login

pytestmark = pytest.mark.asyncio


class MemoryStorage:
    pass


async def test_ai_metrics_use_only_configured_model_aliases_and_bounded_labels() -> (
    None
):
    settings = Settings(
        database_url="sqlite+aiosqlite://",
        n8n_webhook_url="http://n8n:5678/enrich",
        ai_enrichment_route="n8n:approved-alias",
    )
    assert configured_model_alias(settings, "n8n", "approved-alias") == "approved-alias"
    assert configured_model_alias(settings, "n8n", "user/arbitrary-model") == "other"

    client = httpx.AsyncClient(
        transport=httpx.MockTransport(
            lambda request: httpx.Response(
                200,
                json={
                    "schema_version": 1,
                    "summary": "Observed summary.",
                    "usage": {"input_tokens": 4, "output_tokens": 2, "total_tokens": 6},
                },
                request=request,
            )
        )
    )
    processor = ContentProcessor(
        MemoryStorage(),  # type: ignore[arg-type]
        settings=settings,
        enrichment_client=client,
    )
    await processor.process(
        ExtractionInput(
            item_id="private-item-id-must-not-be-a-label",
            item_type=ItemType.TEXT,
            url=None,
            asset_keys=(),
            raw_text="Private metric source content.",
        )
    )
    await client.aclose()
    metrics = generate_latest().decode()
    assert 'provider="n8n"' in metrics
    assert 'model_alias="approved-alias"' in metrics
    assert 'task="enrichment"' in metrics
    assert "private-item-id-must-not-be-a-label" not in metrics
    assert "Private metric source content" not in metrics


async def test_queue_metrics_and_heartbeat_distinguish_idle_from_stopped(
    tmp_path: Path,
) -> None:
    engine = create_async_engine(f"sqlite+aiosqlite:///{tmp_path / 'metrics.db'}")
    factory = async_sessionmaker(engine, expire_on_commit=False)
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
    old = datetime.now(timezone.utc) - timedelta(minutes=12)
    async with factory() as session:
        user = User(email="metrics@example.com", hashed_password="hash")
        item = Item(
            user=user,
            type=ItemType.TEXT,
            raw_text="Queue state.",
            processing_status=ProcessingStatus.READY,
        )
        session.add(item)
        await session.flush()
        session.add(
            ProcessingJob(
                item_id=item.id,
                kind="text",
                analysis_version=item.analysis_version,
                execution_backend="database",
                reason="capture",
                status="pending",
                created_at=old,
                updated_at=old,
                next_attempt_at=old,
            )
        )
        await session.commit()

    WORKER_HEARTBEAT.labels("database_worker").set(time.time() - 120)
    stopped_value = WORKER_HEARTBEAT.labels("database_worker")._value.get()
    mark_worker_heartbeat("database_worker")
    idle_value = WORKER_HEARTBEAT.labels("database_worker")._value.get()
    await update_queue_metrics(factory, backend="database")
    metrics = generate_latest().decode()

    assert idle_value > stopped_value
    assert 'memoryhive_analysis_queue_pending{backend="database"} 1.0' in metrics
    assert "memoryhive_analysis_queue_oldest_age_seconds" in metrics
    await engine.dispose()


async def test_api_request_id_is_captured_as_analysis_correlation_id(
    api_client_with_db: tuple[httpx.AsyncClient, FakeStorage, async_sessionmaker],
) -> None:
    client, _storage, factory = api_client_with_db
    _user, headers = await register_and_login(client, "correlation@example.com")
    headers = {**headers, "X-Request-ID": "capture-correlation-123"}
    response = await client.post(
        "/api/v1/items",
        json={"type": "text", "raw_text": "Correlated capture."},
        headers=headers,
    )
    async with factory() as session:
        job = await session.scalar(
            select(ProcessingJob).where(ProcessingJob.item_id == response.json()["id"])
        )
    assert response.headers["X-Request-ID"] == "capture-correlation-123"
    assert job is not None
    assert job.correlation_id == "capture-correlation-123"
