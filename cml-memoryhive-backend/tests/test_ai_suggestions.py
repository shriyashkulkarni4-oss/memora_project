"""Reversible, offline-idempotent AI suggestion behavior."""

from datetime import datetime, timezone

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.ai.contracts import AnalysisResult
from app.config import Settings
from app.models import EnrichmentRecord, Item
from app.services import analysis as analysis_service
from app.services.analysis import apply_processing_result, persist_enrichment_record
from tests.conftest import FakeStorage

pytestmark = pytest.mark.asyncio


async def _session(client: AsyncClient, email: str) -> tuple[dict, dict[str, str]]:
    user = await client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": "correct-horse-battery", "name": "User"},
    )
    login = await client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": "correct-horse-battery"},
    )
    return user.json(), {"Authorization": f"Bearer {login.json()['access_token']}"}


def enrichment(user_id: str, item_id: str, version: int) -> EnrichmentRecord:
    return EnrichmentRecord(
        user_id=user_id,
        item_id=item_id,
        analysis_version=version,
        schema_version=1,
        taxonomy_version=1,
        summary="PostgreSQL indexing guide",
        topics=["PostgreSQL", "query planning"],
        suggested_tags=["postgresql", "database"],
        classification="reference",
        entities=["PostgreSQL"],
        key_phrases=["query planning"],
        content_language="en",
        confidence=0.95,
        warnings=[],
        provider="openrouter",
        model="approved-model",
        prompt_version="enrichment-v1",
        content_hash="a" * 64,
        field_provenance={},
        generated_at=datetime.now(timezone.utc),
    )


async def test_suggestion_decisions_are_reversible_private_and_idempotent(
    api_client_with_db: tuple[
        AsyncClient, FakeStorage, async_sessionmaker[AsyncSession]
    ],
) -> None:
    client, _storage, session_factory = api_client_with_db
    user, headers = await _session(client, "suggestions@example.com")
    _other, other_headers = await _session(client, "suggestions-other@example.com")
    created = await client.post(
        "/api/v1/items",
        json={"type": "text", "raw_text": "PostgreSQL query planning uses indexes."},
        headers=headers,
    )
    item_id = created.json()["id"]
    async with session_factory() as session:
        session.add(enrichment(user["id"], item_id, 1))
        await session.commit()

    assert (
        await client.get(f"/api/v1/items/{item_id}/suggestions", headers=other_headers)
    ).status_code == 404
    initial = await client.get(f"/api/v1/items/{item_id}/suggestions", headers=headers)
    assert initial.status_code == 200
    assert {entry["status"] for entry in initial.json()["suggestions"]} == {"pending"}

    accept = {
        "client_id": "offline-accept",
        "analysis_version": 1,
        "expected_revision": 1,
        "decisions": [
            {"suggestion_type": "tag", "value": "postgresql", "action": "accept"},
            {
                "suggestion_type": "classification",
                "value": "reference",
                "action": "accept",
            },
        ],
    }
    accepted = await client.post(
        f"/api/v1/items/{item_id}/suggestions/decisions", json=accept, headers=headers
    )
    assert accepted.status_code == 200, accepted.text
    assert accepted.json()["item_revision"] == 2
    duplicate = await client.post(
        f"/api/v1/items/{item_id}/suggestions/decisions", json=accept, headers=headers
    )
    assert duplicate.status_code == 200
    assert duplicate.json()["item_revision"] == 2
    item = await client.get(f"/api/v1/items/{item_id}", headers=headers)
    assert [tag["name"] for tag in item.json()["tags"]] == ["postgresql"]
    assert item.json()["category_id"] is None

    conflict = await client.post(
        f"/api/v1/items/{item_id}/suggestions/decisions",
        json={
            "client_id": "stale-device",
            "analysis_version": 1,
            "expected_revision": 1,
            "decisions": [
                {"suggestion_type": "tag", "value": "database", "action": "reject"}
            ],
        },
        headers=headers,
    )
    assert conflict.status_code == 409

    # A manual tag save clears AI ownership. Undo must not remove the user's tag.
    manual = await client.patch(
        f"/api/v1/items/{item_id}",
        json={"expected_revision": 2, "tags": ["postgresql"]},
        headers=headers,
    )
    assert manual.status_code == 200
    undone = await client.post(
        f"/api/v1/items/{item_id}/suggestions/decisions",
        json={
            "client_id": "offline-undo",
            "analysis_version": 1,
            "expected_revision": 3,
            "decisions": [
                {"suggestion_type": "tag", "value": "postgresql", "action": "undo"}
            ],
        },
        headers=headers,
    )
    assert undone.status_code == 200, undone.text
    item = await client.get(f"/api/v1/items/{item_id}", headers=headers)
    assert [tag["name"] for tag in item.json()["tags"]] == ["postgresql"]

    never = await client.post(
        f"/api/v1/items/{item_id}/suggestions/decisions",
        json={
            "client_id": "offline-never",
            "analysis_version": 1,
            "expected_revision": 4,
            "decisions": [
                {"suggestion_type": "tag", "value": "database", "action": "never"}
            ],
        },
        headers=headers,
    )
    assert never.status_code == 200
    assert (
        next(
            entry
            for entry in never.json()["suggestions"]
            if entry["value"] == "database"
        )["status"]
        == "never"
    )

    # Reanalysis retains immutable old output and applies the global preference.
    async with session_factory() as session:
        record_item = await session.get(Item, item_id)
        assert record_item
        record_item.analysis_version = 2
        session.add(enrichment(user["id"], item_id, 2))
        await session.commit()
    next_version = await client.get(
        f"/api/v1/items/{item_id}/suggestions", headers=headers
    )
    assert next_version.json()["analysis_version"] == 2
    assert (
        next(
            entry
            for entry in next_version.json()["suggestions"]
            if entry["value"] == "database"
        )["status"]
        == "never"
    )


async def test_explicit_confidence_threshold_auto_applies_with_provenance(
    api_client_with_db: tuple[
        AsyncClient, FakeStorage, async_sessionmaker[AsyncSession]
    ],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    client, _storage, session_factory = api_client_with_db
    user, headers = await _session(client, "suggestions-auto@example.com")
    created = await client.post(
        "/api/v1/items",
        json={"type": "text", "raw_text": "PostgreSQL indexing guide."},
        headers=headers,
    )
    item_id = created.json()["id"]
    monkeypatch.setattr(
        analysis_service,
        "get_settings",
        lambda: Settings(
            database_url="sqlite+aiosqlite://",
            ai_suggestion_auto_apply_threshold=0.9,
        ),
    )
    result = AnalysisResult(
        extracted_text="PostgreSQL indexing guide.",
        normalized_text="postgresql indexing guide.",
        language="en",
        summary="PostgreSQL indexing guide.",
        metadata={
            "enrichment": {
                "schema_version": 1,
                "summary": "PostgreSQL indexing guide.",
                "summary_source": "model",
                "suggested_tags": ["postgresql"],
                "topics": ["PostgreSQL"],
                "entities": ["PostgreSQL"],
                "key_phrases": ["indexing guide"],
                "classification": "reference",
                "content_language": "en",
                "confidence": 0.95,
                "warnings": [],
                "provider": "openrouter",
                "model": "approved-model",
            }
        },
        enrichment_attempted=True,
        enrichment_succeeded=True,
    )
    completed_at = datetime.now(timezone.utc)
    async with session_factory() as session:
        item = await session.get(Item, item_id)
        assert item and item.user_id == user["id"]
        apply_processing_result(item, result, completed_at=completed_at)
        await persist_enrichment_record(
            session, item, result, completed_at=completed_at
        )
        await session.commit()

    updated = await client.get(f"/api/v1/items/{item_id}", headers=headers)
    assert [tag["name"] for tag in updated.json()["tags"]] == ["postgresql"]
    suggestions = await client.get(
        f"/api/v1/items/{item_id}/suggestions", headers=headers
    )
    tag = next(
        entry
        for entry in suggestions.json()["suggestions"]
        if entry["value"] == "postgresql"
    )
    assert tag["status"] == "accepted"
    assert tag["can_undo"] is True
