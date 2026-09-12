"""Budgeted, latency-bounded optional reranking across capable providers."""

import asyncio
import time
import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.ai.budgets import DatabaseBudgetGuard
from app.ai.contracts import RerankCandidate, RerankRequest
from app.ai.gateway import (
    AIGateway,
    ProviderError,
    ProviderErrorCode,
    ProviderUsage,
)
from app.ai.policy import AITask, resolve_task_policy
from app.config import Settings
from app.models import User
from app.observability import (
    AI_CALLS,
    AI_COST,
    AI_LATENCY,
    AI_TOKENS,
    configured_model_alias,
)


class RerankingPipeline:
    def __init__(
        self,
        session_factory: async_sessionmaker[AsyncSession],
        gateway: AIGateway,
        settings: Settings,
        budget_guard: DatabaseBudgetGuard,
    ) -> None:
        self.session_factory = session_factory
        self.gateway = gateway
        self.settings = settings
        self.budget_guard = budget_guard

    async def rerank(
        self,
        query: str,
        candidates: list[RerankCandidate],
        *,
        user_id: str,
    ) -> tuple[str, ...]:
        bounded = candidates[: self.settings.ai_rerank_candidate_limit]
        async with self.session_factory() as session:
            external_allowed = bool(
                await session.scalar(
                    select(User.ai_external_processing_allowed).where(
                        User.id == user_id
                    )
                )
            )
        policy = resolve_task_policy(
            self.settings,
            self.gateway,
            AITask.RERANKING,
            external_allowed_for_user=external_allowed,
        )
        routes = ([policy.primary] if policy.primary else []) + list(policy.fallbacks)
        last_error: ProviderError | None = None
        for route in routes:
            if route is None or route.model is None:
                continue
            reservation = await self.budget_guard.reserve(
                operation_key=f"search-rerank:{uuid.uuid4()}",
                user_id=user_id,
                item_id=None,
                task=AITask.RERANKING.value,
                provider=route.provider,
                model=route.model,
                estimated_tokens=max(
                    1,
                    (len(query) + sum(len(candidate.text) for candidate in bounded))
                    // 4,
                ),
            )
            labels = (
                route.provider.value,
                configured_model_alias(
                    self.settings, route.provider.value, route.model
                ),
                AITask.RERANKING.value,
            )
            started = time.perf_counter()
            try:
                async with asyncio.timeout(
                    self.settings.ai_rerank_latency_budget_ms / 1_000
                ):
                    result = await self.gateway.rerank(
                        route.provider,
                        RerankRequest(query, bounded, route.model),
                    )
                usage = ProviderUsage(
                    input_tokens=int(result.usage.get("input_tokens") or 0),
                    output_tokens=int(result.usage.get("output_tokens") or 0),
                    total_tokens=int(result.usage.get("total_tokens") or 0),
                    estimated_cost_usd=float(
                        result.usage.get("estimated_cost_usd") or 0
                    ),
                )
                await self.budget_guard.complete(reservation, usage)
                AI_CALLS.labels(*labels, "success").inc()
                AI_LATENCY.labels(*labels, "success").observe(
                    time.perf_counter() - started
                )
                AI_TOKENS.labels(*labels, "input").inc(usage.input_tokens or 0)
                AI_TOKENS.labels(*labels, "output").inc(usage.output_tokens or 0)
                AI_COST.labels(*labels).inc(usage.estimated_cost_usd or 0)
                return tuple(result.ordered_item_ids)
            except TimeoutError:
                error = ProviderError(ProviderErrorCode.TIMEOUT, route.provider)
            except ProviderError as exc:
                error = exc
            await self.budget_guard.complete(reservation, ProviderUsage(), failed=True)
            AI_CALLS.labels(*labels, "failed").inc()
            AI_LATENCY.labels(*labels, "failed").observe(time.perf_counter() - started)
            last_error = error
        if last_error:
            raise last_error
        return tuple(candidate.item_id for candidate in bounded)
