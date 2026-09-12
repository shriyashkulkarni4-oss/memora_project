"""Golden quality gates and durable structured-enrichment tests."""

import json
import re
from datetime import datetime, timezone
from pathlib import Path

import pytest
from httpx import AsyncClient
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.ai.contracts import AnalysisResult, EnrichmentResult
from app.ai.structured_enrichment import faithfulness_score, normalize_enrichment
from app.models import EnrichmentRecord, Item
from app.services.analysis import apply_processing_result, persist_enrichment_record
from tests.conftest import FakeStorage

pytestmark = pytest.mark.asyncio
FIXTURES = json.loads(
    (Path(__file__).parent / "fixtures" / "enrichment_golden.json").read_text(
        encoding="utf-8"
    )
)


@pytest.mark.parametrize("fixture", FIXTURES, ids=lambda value: value["name"])
async def test_golden_enrichment_is_grounded_and_schema_valid(fixture: dict) -> None:
    result = normalize_enrichment(
        EnrichmentResult(
            **fixture["output"],
            attempted=True,
            succeeded=True,
            provider="openrouter",
            model="approved-model",
        ),
        source_text=fixture["source"],
        content_language="en",
        existing_tags=fixture["existing_tags"],
    )
    assert result.classification == fixture["expected_classification"]
    assert result.content_language == "en"
    source_tokens = set(re.findall(r"[\w'-]+", fixture["source"].casefold()))
    assert (
        faithfulness_score(result.summary, source_tokens)
        >= fixture["minimum_faithfulness"]
    )
    assert "quantum computing" not in result.topics
    assert "astronomy" not in result.suggested_tags
    assert "NASA" not in result.entities


async def test_structured_enrichment_is_versioned_idempotent_and_provenanced(
    api_client_with_db: tuple[
        AsyncClient, FakeStorage, async_sessionmaker[AsyncSession]
    ],
) -> None:
    client, _storage, session_factory = api_client_with_db
    await client.post(
        "/api/v1/auth/register",
        json={
            "email": "enrichment@example.com",
            "password": "correct-horse-battery",
            "name": "Enrichment",
        },
    )
    login = await client.post(
        "/api/v1/auth/login",
        json={"email": "enrichment@example.com", "password": "correct-horse-battery"},
    )
    headers = {"Authorization": f"Bearer {login.json()['access_token']}"}
    created = await client.post(
        "/api/v1/items",
        json={"type": "text", "raw_text": "PostgreSQL query planning uses indexes."},
        headers=headers,
    )
    item_id = created.json()["id"]
    completed_at = datetime.now(timezone.utc)
    result = AnalysisResult(
        extracted_text="PostgreSQL query planning uses indexes.",
        normalized_text="postgresql query planning uses indexes.",
        language="en",
        summary="PostgreSQL query planning uses indexes.",
        metadata={
            "enrichment": {
                "schema_version": 1,
                "summary": "PostgreSQL query planning uses indexes.",
                "detailed_summary": None,
                "topics": ["PostgreSQL"],
                "suggested_tags": ["postgresql"],
                "classification": "reference",
                "entities": ["PostgreSQL"],
                "key_phrases": ["query planning"],
                "content_language": "en",
                "confidence": 0.9,
                "warnings": [],
                "provider": "openrouter",
                "model": "approved-model",
            }
        },
        enrichment_attempted=True,
        enrichment_succeeded=True,
    )
    async with session_factory() as session:
        item = await session.get(Item, item_id)
        assert item
        apply_processing_result(item, result, completed_at=completed_at)
        first = await persist_enrichment_record(
            session, item, result, completed_at=completed_at
        )
        await session.flush()
        second = await persist_enrichment_record(
            session, item, result, completed_at=completed_at
        )
        await session.commit()
        assert first.id == second.id
        assert await session.scalar(select(func.count(EnrichmentRecord.id))) == 1
        record = await session.scalar(select(EnrichmentRecord))
        assert record
        assert record.classification == "reference"
        assert record.field_provenance["summary"]["provider"] == "openrouter"
        assert record.field_provenance["summary"]["generated_at"]

    history = await client.get(f"/api/v1/items/{item_id}/enrichments", headers=headers)
    assert history.status_code == 200
    assert history.json()[0]["taxonomy_version"] == 1
    assert history.json()[0]["field_provenance"]["summary"]["provider"] == "openrouter"


async def test_degraded_fallback_does_not_replace_a_valid_prior_summary() -> None:
    item = Item(
        id="item-1",
        user_id="user-1",
        type="text",
        raw_text="Source text",
        summary="Previously validated summary",
        analysis_version=2,
        revision=1,
    )
    result = AnalysisResult(
        extracted_text="Source text",
        summary="Source text",
        enrichment_attempted=True,
        enrichment_succeeded=False,
        enrichment_errors=["openrouter:timeout"],
    )
    apply_processing_result(item, result, completed_at=datetime.now(timezone.utc))
    assert item.summary == "Previously validated summary"
