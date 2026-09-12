"""Private related, duplicate, resurfacing, diversity, and feedback behavior."""

from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy import delete, func, select, update

from app.config import Settings
from app.models import EmbeddingIndex, Item, ItemEmbedding, ItemInteraction
from tests.test_core_api import register_and_login

pytestmark = pytest.mark.asyncio


async def capture(client, headers, title: str, text: str, source: str, tags=None):
    response = await client.post(
        "/api/v1/items",
        headers=headers,
        json={
            "type": "text",
            "title": title,
            "raw_text": text,
            "source": source,
            "tags": tags or [],
        },
    )
    assert response.status_code == 201
    return response.json()


async def test_memory_feature_flags_are_independently_reversible(
    api_client_with_db, monkeypatch: pytest.MonkeyPatch
) -> None:
    client, _storage, _factory = api_client_with_db
    _owner, headers = await register_and_login(client, "memory-flags@example.com")
    item = await capture(client, headers, "Flagged", "Source remains", "notes")
    disabled = Settings(
        database_url="sqlite+aiosqlite://",
        ai_related_items_enabled=False,
        ai_resurfacing_enabled=False,
    )
    from app.api.v1 import items as items_api

    monkeypatch.setattr(items_api, "get_settings", lambda: disabled)
    assert (
        await client.get(f"/api/v1/items/{item['id']}/related", headers=headers)
    ).status_code == 404
    assert (
        await client.get("/api/v1/items/resurfacing", headers=headers)
    ).status_code == 404


async def test_related_and_duplicate_candidates_are_explainable_and_owner_scoped(
    api_client_with_db, monkeypatch: pytest.MonkeyPatch
) -> None:
    client, _storage, factory = api_client_with_db
    owner, headers = await register_and_login(client, "memory-owner@example.com")
    other, other_headers = await register_and_login(client, "memory-other@example.com")
    source = await capture(
        client,
        headers,
        "Temporal recovery",
        "Durable workflows preserve state after failures.",
        "engineering",
        ["temporal"],
    )
    exact = await capture(
        client,
        headers,
        "Copied note",
        "Durable workflows preserve state after failures.",
        "notes",
    )
    related = await capture(
        client,
        headers,
        "Process resilience",
        "Event history lets orchestration resume safely.",
        "engineering",
        ["temporal"],
    )
    foreign = await capture(
        client,
        other_headers,
        "Private match",
        "Durable workflows preserve state after failures.",
        "engineering",
        ["temporal"],
    )
    configured = Settings(
        database_url="sqlite+aiosqlite://",
        ollama_base_url="http://localhost:11434",
        ollama_embedding_model="embed-v1",
        ai_embeddings_route="ollama:embed-v1",
        ai_embedding_dimensions=3,
        ai_duplicate_semantic_threshold=0.9,
    )
    from app.api.v1 import items as items_api

    monkeypatch.setattr(items_api, "get_settings", lambda: configured)
    async with factory() as session:
        index = EmbeddingIndex(
            provider="ollama",
            model="embed-v1",
            dimensions=3,
            normalization="l2",
            version=1,
        )
        session.add(index)
        await session.flush()
        for record, user_id, vector in (
            (source, owner["id"], [1.0, 0.0, 0.0]),
            (related, owner["id"], [0.99, 0.01, 0.0]),
            (foreign, other["id"], [1.0, 0.0, 0.0]),
        ):
            session.add(
                ItemEmbedding(
                    user_id=user_id,
                    item_id=record["id"],
                    analysis_version=1,
                    chunk_id=f"{record['id']}:0:test",
                    index_id=index.id,
                    provider="ollama",
                    model="embed-v1",
                    dimensions=3,
                    normalization="l2",
                    index_version=1,
                    vector=vector,
                    content_hash=f"hash-{record['id']}",
                )
            )
        await session.commit()

    duplicates = await client.get(
        f"/api/v1/items/{source['id']}/duplicates", headers=headers
    )
    assert duplicates.status_code == 200
    duplicate_by_id = {value["item"]["id"]: value for value in duplicates.json()}
    assert duplicate_by_id[exact["id"]]["duplicate_kind"] == "exact_content"
    assert duplicate_by_id[related["id"]]["duplicate_kind"] == "near_semantic"
    assert foreign["id"] not in duplicate_by_id

    related_response = await client.get(
        f"/api/v1/items/{source['id']}/related", headers=headers
    )
    related_by_id = {value["item"]["id"]: value for value in related_response.json()}
    assert "semantically similar content" in related_by_id[related["id"]]["reasons"]
    assert any(
        reason.startswith("shared concepts")
        for reason in related_by_id[related["id"]]["reasons"]
    )
    assert foreign["id"] not in related_by_id


async def test_resurfacing_feedback_is_reversible_frequency_capped_and_diverse(
    api_client_with_db,
) -> None:
    client, _storage, factory = api_client_with_db
    _owner, headers = await register_and_login(client, "resurface@example.com")
    records = []
    for index, source in enumerate(("source-a", "source-a", "source-a", "source-b")):
        records.append(
            await capture(
                client,
                headers,
                f"Memory {index}",
                f"Useful saved thought {index}",
                source,
                [f"topic-{index}"],
            )
        )
    async with factory() as session:
        for index, record in enumerate(records):
            item = await session.get(Item, record["id"])
            assert item is not None
            item.created_at = datetime.now(timezone.utc) - timedelta(days=90 - index)
        await session.commit()

    first = await client.get("/api/v1/items/resurfacing", headers=headers)
    assert first.status_code == 200
    matches = first.json()["items"]
    assert matches
    assert all(value["reasons"] for value in matches)
    assert sum(value["item"]["source"] == "source-a" for value in matches) <= 2
    immediate = await client.get("/api/v1/items/resurfacing", headers=headers)
    assert {value["item"]["id"] for value in matches}.isdisjoint(
        {value["item"]["id"] for value in immediate.json()["items"]}
    )
    target = matches[0]["item"]

    dismissed = await client.post(
        f"/api/v1/items/resurfacing/{target['id']}/feedback",
        headers=headers,
        json={"action": "dismiss", "client_id": "dismiss-1"},
    )
    assert dismissed.status_code == 200
    repeated = await client.post(
        f"/api/v1/items/resurfacing/{target['id']}/feedback",
        headers=headers,
        json={"action": "dismiss", "client_id": "dismiss-1"},
    )
    assert repeated.json()["id"] == dismissed.json()["id"]

    async with factory() as session:
        await session.execute(
            update(ItemInteraction)
            .where(ItemInteraction.action == "shown")
            .values(created_at=datetime.now(timezone.utc) - timedelta(days=8))
        )
        await session.commit()
    after_dismiss = await client.get("/api/v1/items/resurfacing", headers=headers)
    assert target["id"] not in {
        value["item"]["id"] for value in after_dismiss.json()["items"]
    }

    undone = await client.post(
        f"/api/v1/items/resurfacing/{target['id']}/feedback",
        headers=headers,
        json={
            "action": "undo",
            "client_id": "undo-1",
            "reverses_id": dismissed.json()["id"],
        },
    )
    assert undone.status_code == 200
    async with factory() as session:
        await session.execute(
            delete(ItemInteraction).where(ItemInteraction.action == "shown")
        )
        await session.commit()
    after_undo = await client.get("/api/v1/items/resurfacing", headers=headers)
    assert target["id"] in {value["item"]["id"] for value in after_undo.json()["items"]}

    deleted = await client.delete(f"/api/v1/items/{target['id']}", headers=headers)
    assert deleted.status_code == 204
    async with factory() as session:
        remaining = await session.scalar(
            select(func.count(ItemInteraction.id)).where(
                ItemInteraction.subject_item_id == target["id"]
            )
        )
    assert remaining == 0
