"""Versioned analysis-contract and stage-boundary tests."""

import json
from dataclasses import FrozenInstanceError

import httpx
import pytest
from temporalio.converter import DataConverter

from app.ai.contracts import (
    ANALYSIS_CONTRACT_VERSION,
    EmbeddingResult,
    EnrichmentRequest,
    EnrichmentResult,
    ExtractedDocument,
    ExtractionInput,
    chunk_document,
)
from app.config import Settings
from app.models import ItemType
from app.services.processing import ContentProcessor
from tests.test_processing import MemoryStorage


def test_extraction_input_has_deterministic_temporal_safe_payload() -> None:
    value = ExtractionInput(
        item_id="item-1",
        item_type=ItemType.TEXT,
        url=None,
        asset_keys=["second", "first"],
        raw_text="नमस्ते 🌍",
        analysis_version=3,
    )

    assert value.asset_keys == ("second", "first")
    assert value.contract_version == ANALYSIS_CONTRACT_VERSION
    assert json.dumps(
        value.to_payload(), sort_keys=True, ensure_ascii=False
    ) == json.dumps(value.to_payload(), sort_keys=True, ensure_ascii=False)
    with pytest.raises(FrozenInstanceError):
        value.item_id = "changed"  # type: ignore[misc]


def test_enrichment_contract_rejects_malformed_or_unbounded_output() -> None:
    with pytest.raises(ValueError, match="between 0 and 1"):
        EnrichmentResult(attempted=True, succeeded=True, confidence=1.5)
    with pytest.raises(ValueError, match="list of strings"):
        EnrichmentResult(attempted=True, suggested_tags="not-a-list")  # type: ignore[arg-type]
    with pytest.raises(ValueError, match="must be attempted"):
        EnrichmentResult(succeeded=True)
    with pytest.raises(ValueError, match="20 items"):
        EnrichmentResult(topics=[f"topic-{index}" for index in range(21)])


def test_large_unicode_enrichment_and_chunking_are_bounded_and_stable() -> None:
    text = ("ज्ञान 🌍 memory retrieval " * 5_000).strip()
    request = EnrichmentRequest(
        item_id="unicode-item",
        analysis_version=2,
        text=text,
        notes="महत्वपूर्ण note",
        max_characters=10_000,
    )
    assert len(request.text) == 10_000
    assert len(request.contextual_text) <= 10_000

    document = ExtractedDocument(
        item_id=request.item_id,
        analysis_version=request.analysis_version,
        extracted_text=text,
        normalized_text=text.casefold(),
        language="hi",
    )
    first = chunk_document(document, maximum_characters=400, overlap=40)
    second = chunk_document(document, maximum_characters=400, overlap=40)
    assert first == second
    assert len(first) > 1
    assert all(len(chunk.text) <= 400 for chunk in first)
    assert len({chunk.content_hash for chunk in first}) > 1


def test_embedding_contract_rejects_dimension_drift_and_non_finite_values() -> None:
    with pytest.raises(ValueError, match="dimensions"):
        EmbeddingResult(
            chunk_id="chunk-1",
            model_alias="embedding-v1",
            dimensions=3,
            vector=[0.1, 0.2],
            provider="test",
        )
    with pytest.raises(ValueError, match="finite"):
        EmbeddingResult(
            chunk_id="chunk-1",
            model_alias="embedding-v1",
            dimensions=2,
            vector=[0.1, float("nan")],
            provider="test",
        )


@pytest.mark.asyncio
async def test_contracts_round_trip_through_temporal_data_converter() -> None:
    value = ExtractionInput(
        item_id="temporal-contract",
        item_type=ItemType.TEXT,
        url=None,
        asset_keys=("asset-1",),
        raw_text="Deterministic payload",
        notes="User context",
        analysis_version=4,
    )
    payloads = await DataConverter.default.encode([value])
    decoded = await DataConverter.default.decode(payloads, [ExtractionInput])

    assert decoded == [value]


@pytest.mark.asyncio
async def test_empty_extraction_has_a_valid_no_enrichment_result() -> None:
    processor = ContentProcessor(MemoryStorage())  # type: ignore[arg-type]

    result = await processor.process(
        ExtractionInput(
            item_id="empty-item",
            item_type=ItemType.TEXT,
            url=None,
            asset_keys=(),
            raw_text="",
        )
    )

    assert result.extracted_text is None
    assert result.summary is None
    assert result.enrichment_attempted is False
    assert result.enrichment_succeeded is False


@pytest.mark.asyncio
async def test_malformed_n8n_output_cannot_partially_mutate_analysis_result() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/enrich"
        return httpx.Response(
            200,
            json={
                "schema_version": 1,
                "summary": "This must not be partially accepted.",
                "tags": "invalid-string-instead-of-list",
            },
            request=request,
        )

    client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    processor = ContentProcessor(
        MemoryStorage(),  # type: ignore[arg-type]
        settings=Settings(
            database_url="sqlite+aiosqlite://",
            n8n_webhook_url="https://n8n.example.test/enrich",
            ai_enrichment_route="n8n",
        ),
        enrichment_client=client,
    )
    result = await processor.process(
        ExtractionInput(
            item_id="item-1",
            item_type=ItemType.TEXT,
            url=None,
            asset_keys=(),
            raw_text="The deterministic fallback remains intact.",
        )
    )
    await client.aclose()

    assert result.summary == "The deterministic fallback remains intact."
    assert result.enrichment_attempted is True
    assert result.enrichment_succeeded is False
    assert result.enrichment_errors == ("n8n:malformed_response",)
    assert result.metadata["enrichment"]["suggested_tags"] == []


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "payload", [{"schema_version": 1}, {"schema_version": 1, "summary": "   "}]
)
async def test_empty_or_refused_enrichment_uses_explicit_degraded_fallback(
    payload: dict[str, str],
) -> None:
    client = httpx.AsyncClient(
        transport=httpx.MockTransport(
            lambda request: httpx.Response(200, json=payload, request=request)
        )
    )
    processor = ContentProcessor(
        MemoryStorage(),  # type: ignore[arg-type]
        settings=Settings(
            database_url="sqlite+aiosqlite://",
            n8n_webhook_url="https://n8n.example.test/enrich",
            ai_enrichment_route="n8n",
        ),
        enrichment_client=client,
    )
    result = await processor.process(
        ExtractionInput(
            item_id="item-1",
            item_type=ItemType.TEXT,
            url=None,
            asset_keys=(),
            raw_text="Fallback content remains available.",
        )
    )
    await client.aclose()

    assert result.summary == "Fallback content remains available."
    assert result.enrichment_attempted is True
    assert result.enrichment_succeeded is False
    assert result.enrichment_errors == ("n8n:content_refusal",)
