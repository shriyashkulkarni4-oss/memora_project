"""AI run audit, provenance, export, and lifecycle regression tests."""

import io
import json
import zipfile
from pathlib import Path

import httpx
import pytest
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.ai.audit import AIRunRecorder, content_fingerprint
from app.ai.contracts import ExtractionInput
from app.config import Settings
from app.database import Base
from app.models import (
    AIFieldProvenance,
    AIRun,
    EmbeddingIndex,
    ItemEmbedding,
    ItemType,
)
from app.services.processing import ContentProcessor
from tests.conftest import FakeStorage
from tests.test_core_api import register_and_login

pytestmark = pytest.mark.asyncio


class MemoryStorage:
    pass


async def audit_database(tmp_path: Path):
    engine = create_async_engine(f"sqlite+aiosqlite:///{tmp_path / 'audit.db'}")
    factory = async_sessionmaker(engine, expire_on_commit=False)
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
    return engine, factory


async def test_model_invocation_records_content_free_run_and_field_provenance(
    tmp_path: Path,
) -> None:
    engine, factory = await audit_database(tmp_path)
    secret_content = "Private source content that must not appear in the audit row."

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json={
                "schema_version": 1,
                "summary": "Safe generated summary.",
                "tags": ["private-memory"],
                "classification": "reference",
                "entities": ["Memoryhive"],
                "usage": {
                    "input_tokens": 10,
                    "output_tokens": 4,
                    "total_tokens": 14,
                    "estimated_cost_usd": 0.002,
                },
            },
            headers={"x-request-id": "audit-request"},
            request=request,
        )

    client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    settings = Settings(
        database_url="sqlite+aiosqlite://",
        n8n_webhook_url="http://n8n:5678/enrich",
        ai_enrichment_route="n8n",
    )
    processor = ContentProcessor(
        MemoryStorage(),  # type: ignore[arg-type]
        settings=settings,
        enrichment_client=client,
        run_recorder=AIRunRecorder(factory),
    )
    result = await processor.process(
        ExtractionInput(
            item_id="item-audit",
            item_type=ItemType.TEXT,
            url=None,
            asset_keys=(),
            raw_text=secret_content,
            user_id=None,
            analysis_job_id=None,
            workflow_id="workflow-1",
        )
    )
    await client.aclose()

    async with factory() as session:
        run = await session.scalar(select(AIRun))
        fields = set(await session.scalars(select(AIFieldProvenance.field_name)))
    assert run is not None
    assert run.status == "completed"
    assert run.provider == "n8n"
    assert run.workflow_id == "workflow-1"
    assert run.content_hash == content_fingerprint(secret_content)
    assert run.total_tokens == 14
    assert run.estimated_cost_usd == pytest.approx(0.002)
    assert run.encrypted_debug_payload is None
    assert secret_content not in repr(run.__dict__)
    # Unsupported model claims are rejected before provenance is recorded; the
    # deterministically detected language remains a valid generated field.
    assert fields == {"classification", "content_language", "summary"}
    assert result.summary == secret_content
    assert "ungrounded_summary_rejected" in result.metadata["enrichment"]["warnings"]
    await engine.dispose()


async def test_failed_model_and_deterministic_fallback_are_both_audited(
    tmp_path: Path,
) -> None:
    engine, factory = await audit_database(tmp_path)
    client = httpx.AsyncClient(
        transport=httpx.MockTransport(
            lambda request: httpx.Response(401, request=request)
        )
    )
    processor = ContentProcessor(
        MemoryStorage(),  # type: ignore[arg-type]
        settings=Settings(
            database_url="sqlite+aiosqlite://",
            n8n_webhook_url="http://n8n:5678/enrich",
            n8n_api_key="credential-not-for-audit",
            ai_enrichment_route="n8n",
        ),
        enrichment_client=client,
        run_recorder=AIRunRecorder(factory),
    )
    result = await processor.process(
        ExtractionInput(
            item_id="item-fallback",
            item_type=ItemType.TEXT,
            url=None,
            asset_keys=(),
            raw_text="Fallback source.",
        )
    )
    await client.aclose()

    async with factory() as session:
        runs = list(
            (await session.scalars(select(AIRun).order_by(AIRun.started_at))).all()
        )
    assert [(run.provider, run.status) for run in runs] == [
        ("n8n", "failed"),
        ("deterministic", "completed"),
    ]
    assert runs[0].error_code == "authentication"
    assert runs[1].attempts == 0
    assert "credential-not-for-audit" not in repr([run.__dict__ for run in runs])
    assert result.summary == "Fallback source."
    await engine.dispose()


async def test_ai_records_are_exported_and_removed_with_account(
    api_client_with_db: tuple[httpx.AsyncClient, FakeStorage, async_sessionmaker],
) -> None:
    client, _storage, factory = api_client_with_db
    user, headers = await register_and_login(client, "ai-export@example.com")
    captured = await client.post(
        "/api/v1/items",
        json={"type": "text", "raw_text": "Export lifecycle source."},
        headers=headers,
    )
    item = captured.json()
    async with factory() as session:
        run = AIRun(
            user_id=user["id"],
            item_id=item["id"],
            analysis_version=1,
            task="enrichment",
            provider="ollama",
            requested_model="model-alias",
            resolved_model="model-alias",
            content_hash=content_fingerprint("Export lifecycle source."),
            status="completed",
        )
        session.add(run)
        await session.flush()
        embedding_index = EmbeddingIndex(
            provider="ollama",
            model="embedding-alias",
            dimensions=3,
            normalization="l2",
            version=1,
        )
        session.add(embedding_index)
        await session.flush()
        session.add(
            AIFieldProvenance(
                run_id=run.id,
                user_id=user["id"],
                item_id=item["id"],
                analysis_version=1,
                field_name="summary",
                source="model",
                provider="ollama",
                model="model-alias",
            )
        )
        session.add(
            ItemEmbedding(
                user_id=user["id"],
                item_id=item["id"],
                analysis_version=1,
                chunk_id="chunk-1",
                index_id=embedding_index.id,
                provider="ollama",
                model="embedding-alias",
                dimensions=3,
                vector=[0.1, 0.2, 0.3],
                content_hash=content_fingerprint("Export lifecycle source."),
            )
        )
        await session.commit()

    exported = await client.get("/api/v1/account/export", headers=headers)
    with zipfile.ZipFile(io.BytesIO(exported.content)) as archive:
        manifest = json.loads(archive.read("memoryhive-export.json"))
    assert manifest["ai_runs"][0]["provider"] == "ollama"
    assert manifest["ai_field_provenance"][0]["field_name"] == "summary"
    assert manifest["item_embeddings"][0]["vector"] == [0.1, 0.2, 0.3]

    deleted = await client.request(
        "DELETE",
        "/api/v1/account",
        headers=headers,
        json={"password": "correct-horse-battery", "confirmation": "DELETE"},
    )
    assert deleted.status_code == 204
    async with factory() as session:
        assert await session.scalar(select(func.count()).select_from(AIRun)) == 0
        assert (
            await session.scalar(select(func.count()).select_from(ItemEmbedding)) == 0
        )
        assert (
            await session.scalar(select(func.count()).select_from(AIFieldProvenance))
            == 0
        )
