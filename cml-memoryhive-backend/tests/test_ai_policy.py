"""Task routing, privacy, budget, and credential-reference policy tests."""

from dataclasses import dataclass
from pathlib import Path

import pytest
from pydantic import SecretStr, ValidationError
from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.ai.budgets import DatabaseBudgetGuard
from app.ai.contracts import (
    EmbeddingRequest,
    EnrichmentRequest,
    EnrichmentResult,
    ExtractionInput,
)
from app.ai.gateway import (
    AIGateway,
    ProviderCapability,
    ProviderError,
    ProviderErrorCode,
    ProviderHealth,
    ProviderLimits,
    ProviderModel,
    ProviderProvenance,
    ProviderResponse,
    ProviderType,
    ProviderUsage,
)
from app.ai.policy import (
    AITask,
    CredentialReference,
    CredentialScope,
    resolve_task_policy,
)
from app.config import Settings
from app.database import Base
from app.models import AIUsageEvent, ItemType
from app.services.processing import ContentProcessor

pytestmark = pytest.mark.asyncio


@dataclass
class PolicyAdapter:
    provider_type: ProviderType
    capabilities: frozenset[ProviderCapability]
    limits: ProviderLimits = ProviderLimits(maximum_attempts=1)
    fail: bool = False
    calls: int = 0

    async def enrich(
        self, _request: EnrichmentRequest, *, model: str | None
    ) -> ProviderResponse:
        self.calls += 1
        if self.fail:
            raise ProviderError(ProviderErrorCode.UNAVAILABLE, self.provider_type)
        return ProviderResponse(
            EnrichmentResult(
                summary=f"{self.provider_type.value} summary",
                attempted=True,
                succeeded=True,
                provider=self.provider_type.value,
                model=model,
            ),
            ProviderUsage(input_tokens=5, output_tokens=3, total_tokens=8),
            ProviderProvenance(self.provider_type, model),
        )

    async def embed(self, _request: EmbeddingRequest):
        raise ProviderError(
            ProviderErrorCode.UNSUPPORTED_CAPABILITY, self.provider_type
        )

    async def vision(self, _request: object):
        raise ProviderError(
            ProviderErrorCode.UNSUPPORTED_CAPABILITY, self.provider_type
        )

    async def list_models(self) -> tuple[ProviderModel, ...]:
        return ()

    async def health(self) -> ProviderHealth:
        return ProviderHealth(True)


class MemoryStorage:
    pass


def local_settings(**values: object) -> Settings:
    return Settings(
        database_url="sqlite+aiosqlite://",
        ollama_base_url="http://ollama:11434",
        **values,
    )


async def test_every_task_resolves_explicit_provider_model_and_capability() -> None:
    adapter = PolicyAdapter(
        ProviderType.OLLAMA,
        frozenset(
            {
                ProviderCapability.ENRICHMENT,
                ProviderCapability.EMBEDDINGS,
                ProviderCapability.VISION,
            }
        ),
    )
    gateway = AIGateway([adapter])
    settings = local_settings(
        ai_summarization_route="ollama:summary-model",
        ai_enrichment_route="ollama:enrichment-model",
        ai_embeddings_route="ollama:embedding-model",
        ai_reranking_route="ollama:reranking-model",
        ai_vision_route="ollama:vision-model",
    )

    expected_models = {
        AITask.SUMMARIZATION: "summary-model",
        AITask.ENRICHMENT: "enrichment-model",
        AITask.EMBEDDINGS: "embedding-model",
        AITask.RERANKING: "reranking-model",
        AITask.VISION: "vision-model",
    }
    for task in AITask:
        decision = resolve_task_policy(settings, gateway, task)
        assert decision.primary is not None
        assert decision.primary.provider == ProviderType.OLLAMA
        assert decision.primary.model == expected_models[task]

    unsupported = AIGateway(
        [PolicyAdapter(ProviderType.OLLAMA, frozenset({ProviderCapability.ENRICHMENT}))]
    )
    with pytest.raises(ProviderError) as exc:
        resolve_task_policy(settings, unsupported, AITask.EMBEDDINGS)
    assert exc.value.code == ProviderErrorCode.UNSUPPORTED_CAPABILITY

    default_embedding = resolve_task_policy(
        local_settings(
            ollama_embedding_model="nomic-embed-text",
            ai_embeddings_route="ollama",
        ),
        gateway,
        AITask.EMBEDDINGS,
    )
    assert default_embedding.primary is not None
    assert default_embedding.primary.model == "nomic-embed-text"


async def test_fallback_is_disabled_by_default_and_recorded_when_enabled() -> None:
    primary = PolicyAdapter(
        ProviderType.OLLAMA,
        frozenset({ProviderCapability.ENRICHMENT}),
        fail=True,
    )
    fallback = PolicyAdapter(
        ProviderType.N8N, frozenset({ProviderCapability.ENRICHMENT})
    )
    gateway = AIGateway([primary, fallback])
    disabled = local_settings(
        n8n_webhook_url="http://n8n:5678/hook",
        ai_enrichment_route="ollama:primary",
        ai_enrichment_fallback_routes=["n8n"],
    )
    assert resolve_task_policy(disabled, gateway, AITask.ENRICHMENT).fallbacks == ()

    enabled = disabled.model_copy(update={"ai_cross_provider_fallback_enabled": True})
    processor = ContentProcessor(
        MemoryStorage(),  # type: ignore[arg-type]
        settings=enabled,
        ai_gateway=gateway,
    )
    result = await processor.process(
        ExtractionInput(
            item_id="item-1",
            item_type=ItemType.TEXT,
            url=None,
            asset_keys=(),
            raw_text="Deterministic source text remains available.",
        )
    )

    assert primary.calls == 1
    assert fallback.calls == 1
    assert result.enrichment_succeeded is True
    assert result.metadata["enrichment"]["provenance"]["gateway_fallback"] is True


async def test_external_routes_require_explicit_content_permission() -> None:
    with pytest.raises(ValidationError, match="without consent"):
        Settings(
            database_url="sqlite+aiosqlite://",
            openrouter_enabled=True,
            openrouter_api_key=SecretStr("secret"),
            openrouter_model="vendor/model",
            ai_enrichment_route="openrouter",
        )

    settings = Settings(
        database_url="sqlite+aiosqlite://",
        openrouter_enabled=True,
        openrouter_api_key=SecretStr("secret"),
        openrouter_model="vendor/model",
        ai_enrichment_route="openrouter",
        ai_external_content_allowed=True,
        ai_allowed_external_providers=["openrouter"],
    )
    assert settings.ai_external_content_allowed is True


async def test_credential_reference_supports_future_byok_without_plaintext() -> None:
    reference = CredentialReference(
        scope=CredentialScope.USER,
        provider=ProviderType.OPENROUTER,
        reference="vault://users/user-1/openrouter",
    )
    assert reference.reference.startswith("vault://")
    assert "secret" not in repr(reference).lower()


async def test_database_budget_enforces_global_and_per_user_limits(
    tmp_path: Path,
) -> None:
    engine = create_async_engine(f"sqlite+aiosqlite:///{tmp_path / 'budgets.db'}")
    factory = async_sessionmaker(engine, expire_on_commit=False)
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
    guard = DatabaseBudgetGuard(
        factory,
        local_settings(
            ai_daily_request_budget=2,
            ai_daily_token_budget=20,
            ai_per_user_daily_request_quota=1,
        ),
    )

    first = await guard.reserve(
        operation_key="first",
        user_id="user-1",
        item_id=None,
        task="enrichment",
        provider=ProviderType.OLLAMA,
        model="model",
        estimated_tokens=8,
    )
    await guard.complete(first, ProviderUsage(total_tokens=8, estimated_cost_usd=0.1))
    with pytest.raises(ProviderError) as per_user:
        await guard.reserve(
            operation_key="second",
            user_id="user-1",
            item_id=None,
            task="enrichment",
            provider=ProviderType.OLLAMA,
            model="model",
            estimated_tokens=8,
        )
    assert per_user.value.code == ProviderErrorCode.BUDGET_EXCEEDED

    second_user = await guard.reserve(
        operation_key="third",
        user_id="user-2",
        item_id=None,
        task="enrichment",
        provider=ProviderType.OLLAMA,
        model="model",
        estimated_tokens=8,
    )
    await guard.complete(second_user, ProviderUsage(total_tokens=8))
    with pytest.raises(ProviderError):
        await guard.reserve(
            operation_key="fourth",
            user_id="user-3",
            item_id=None,
            task="enrichment",
            provider=ProviderType.OLLAMA,
            model="model",
            estimated_tokens=1,
        )

    async with factory() as session:
        events = list((await session.scalars(select(AIUsageEvent))).all())
    assert len(events) == 2
    assert events[0].cost_usd == pytest.approx(0.1)

    cost_guard = DatabaseBudgetGuard(
        factory, local_settings(ai_daily_cost_budget_usd=0.1)
    )
    with pytest.raises(ProviderError) as cost_limit:
        await cost_guard.reserve(
            operation_key="cost-limited",
            user_id=None,
            item_id=None,
            task="enrichment",
            provider=ProviderType.OLLAMA,
            model="model",
            estimated_tokens=1,
        )
    assert cost_limit.value.code == ProviderErrorCode.BUDGET_EXCEEDED
    await engine.dispose()


async def test_budget_exhaustion_skips_model_but_keeps_deterministic_result() -> None:
    class ExhaustedBudget:
        async def reserve(self, **_kwargs: object):
            raise ProviderError(ProviderErrorCode.BUDGET_EXCEEDED, ProviderType.OLLAMA)

    adapter = PolicyAdapter(
        ProviderType.OLLAMA, frozenset({ProviderCapability.ENRICHMENT})
    )
    processor = ContentProcessor(
        MemoryStorage(),  # type: ignore[arg-type]
        settings=local_settings(ai_enrichment_route="ollama"),
        ai_gateway=AIGateway([adapter]),
        budget_guard=ExhaustedBudget(),  # type: ignore[arg-type]
    )
    result = await processor.process(
        ExtractionInput(
            item_id="item-budget",
            item_type=ItemType.TEXT,
            url=None,
            asset_keys=(),
            raw_text="Deterministic extraction survives exhausted AI budgets.",
        )
    )

    assert adapter.calls == 0
    assert result.summary == "Deterministic extraction survives exhausted AI budgets."
    assert result.enrichment_errors == ("ollama:budget_exceeded",)
