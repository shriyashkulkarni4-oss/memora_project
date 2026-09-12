"""Database-backed AI request/token/cost budgets and per-user quotas."""

from dataclasses import dataclass
from datetime import datetime, timezone

from sqlalchemy import func, select, text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.ai.gateway import ProviderError, ProviderErrorCode, ProviderType, ProviderUsage
from app.config import Settings
from app.models import AIUsageEvent


@dataclass(frozen=True)
class BudgetReservation:
    event_id: str
    operation_key: str


class DatabaseBudgetGuard:
    def __init__(
        self,
        session_factory: async_sessionmaker[AsyncSession],
        settings: Settings,
    ) -> None:
        self.session_factory = session_factory
        self.settings = settings

    async def reserve(
        self,
        *,
        operation_key: str,
        user_id: str | None,
        item_id: str | None,
        task: str,
        provider: ProviderType,
        model: str | None,
        estimated_tokens: int,
    ) -> BudgetReservation:
        async with self.session_factory() as session:
            if session.bind and session.bind.dialect.name == "postgresql":
                # Serialize budget checks and reservations across worker processes.
                await session.execute(text("SELECT pg_advisory_xact_lock(1296387145)"))
            existing = await session.scalar(
                select(AIUsageEvent).where(AIUsageEvent.operation_key == operation_key)
            )
            if existing:
                return BudgetReservation(existing.id, operation_key)
            now = datetime.now(timezone.utc)
            day = now.replace(hour=0, minute=0, second=0, microsecond=0)
            month = day.replace(day=1)
            await self._check_window(
                session,
                provider,
                start=day,
                user_id=None,
                request_limit=self.settings.ai_daily_request_budget,
                token_limit=self.settings.ai_daily_token_budget,
                cost_limit=self.settings.ai_daily_cost_budget_usd,
                estimated_tokens=estimated_tokens,
            )
            await self._check_window(
                session,
                provider,
                start=month,
                user_id=None,
                request_limit=self.settings.ai_monthly_request_budget,
                token_limit=self.settings.ai_monthly_token_budget,
                cost_limit=self.settings.ai_monthly_cost_budget_usd,
                estimated_tokens=estimated_tokens,
            )
            if user_id:
                await self._check_window(
                    session,
                    provider,
                    start=day,
                    user_id=user_id,
                    request_limit=self.settings.ai_per_user_daily_request_quota,
                    token_limit=self.settings.ai_per_user_daily_token_quota,
                    cost_limit=0,
                    estimated_tokens=estimated_tokens,
                )
                await self._check_window(
                    session,
                    provider,
                    start=month,
                    user_id=user_id,
                    request_limit=self.settings.ai_per_user_monthly_request_quota,
                    token_limit=self.settings.ai_per_user_monthly_token_quota,
                    cost_limit=0,
                    estimated_tokens=estimated_tokens,
                )
            event = AIUsageEvent(
                operation_key=operation_key,
                user_id=user_id,
                item_id=item_id,
                task=task,
                provider=provider.value,
                model=model,
                status="reserved",
                total_tokens=estimated_tokens,
                created_at=now,
            )
            session.add(event)
            await session.commit()
            return BudgetReservation(event.id, operation_key)

    async def complete(
        self,
        reservation: BudgetReservation,
        usage: ProviderUsage,
        *,
        failed: bool = False,
    ) -> None:
        async with self.session_factory() as session:
            event = await session.get(AIUsageEvent, reservation.event_id)
            if event is None:
                return
            event.status = "failed" if failed else "completed"
            event.input_tokens = usage.input_tokens or 0
            event.output_tokens = usage.output_tokens or 0
            event.total_tokens = usage.total_tokens or (
                event.input_tokens + event.output_tokens
            )
            event.cost_usd = usage.estimated_cost_usd or 0
            event.completed_at = datetime.now(timezone.utc)
            await session.commit()

    async def _check_window(
        self,
        session: AsyncSession,
        provider: ProviderType,
        *,
        start: datetime,
        user_id: str | None,
        request_limit: int,
        token_limit: int,
        cost_limit: float,
        estimated_tokens: int,
    ) -> None:
        if request_limit <= 0 and token_limit <= 0 and cost_limit <= 0:
            return
        query = select(
            func.count(AIUsageEvent.id),
            func.coalesce(func.sum(AIUsageEvent.total_tokens), 0),
            func.coalesce(func.sum(AIUsageEvent.cost_usd), 0.0),
        ).where(AIUsageEvent.created_at >= start)
        if user_id is not None:
            query = query.where(AIUsageEvent.user_id == user_id)
        requests, tokens, cost = (await session.execute(query)).one()
        if (
            (request_limit > 0 and requests + 1 > request_limit)
            or (token_limit > 0 and tokens + estimated_tokens > token_limit)
            or (cost_limit > 0 and float(cost) >= cost_limit)
        ):
            raise ProviderError(ProviderErrorCode.BUDGET_EXCEEDED, provider)
