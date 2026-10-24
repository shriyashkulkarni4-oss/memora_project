"""Privacy-safe persistence for model and deterministic AI outcomes."""

import hashlib
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.ai.contracts import ENRICHMENT_SCHEMA_VERSION, EnrichmentResult
from app.ai.gateway import ProviderResponse, ProviderType
from app.models import AIFieldProvenance, AIRun


@dataclass(frozen=True)
class AIRunContext:
    user_id: str | None
    item_id: str
    analysis_version: int
    job_id: str | None
    workflow_id: str | None
    correlation_id: str | None
    fallback_chain: tuple[str, ...]


def content_fingerprint(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def generated_fields(result: EnrichmentResult) -> tuple[str, ...]:
    candidates = {
        "summary": result.summary,
        "detailed_summary": result.detailed_summary,
        "suggested_tags": result.suggested_tags,
        "classification": result.classification,
        "entities": result.entities,
        "key_phrases": result.key_phrases,
        "content_language": result.content_language,
    }
    return tuple(name for name, value in candidates.items() if value)


class AIRunRecorder:
    def __init__(self, session_factory: async_sessionmaker[AsyncSession]) -> None:
        self.session_factory = session_factory

    async def start_model_run(
        self,
        context: AIRunContext,
        *,
        task: str,
        provider: ProviderType,
        requested_model: str | None,
        content: str,
        prompt_version: str,
    ) -> str:
        run = AIRun(
            id=str(uuid.uuid4()),
            user_id=context.user_id,
            item_id=context.item_id,
            analysis_version=context.analysis_version,
            job_id=context.job_id,
            workflow_id=context.workflow_id,
            correlation_id=context.correlation_id,
            task=task,
            provider=provider.value,
            requested_model=requested_model,
            prompt_version=prompt_version,
            schema_version=ENRICHMENT_SCHEMA_VERSION,
            content_hash=content_fingerprint(content),
            status="started",
            fallback_chain=list(context.fallback_chain),
        )
        async with self.session_factory() as session:
            session.add(run)
            await session.commit()
        return run.id

    async def complete_model_run(self, run_id: str, response: ProviderResponse) -> None:
        async with self.session_factory() as session:
            run = await session.get(AIRun, run_id)
            if run is None:
                return
            usage = response.usage
            run.status = "completed"
            run.resolved_model = response.provenance.model
            run.latency_ms = response.provenance.latency_ms
            run.finish_reason = response.provenance.finish_reason
            run.input_tokens = usage.input_tokens or 0
            run.output_tokens = usage.output_tokens or 0
            run.total_tokens = usage.total_tokens or (
                run.input_tokens + run.output_tokens
            )
            run.estimated_cost_usd = usage.estimated_cost_usd or 0
            run.completed_at = datetime.now(timezone.utc)
            session.add_all(
                AIFieldProvenance(
                    run_id=run.id,
                    user_id=run.user_id,
                    item_id=run.item_id,
                    analysis_version=run.analysis_version,
                    field_name=field_name,
                    source="model",
                    provider=run.provider,
                    model=run.resolved_model,
                )
                for field_name in generated_fields(response.enrichment)
            )
            await session.commit()

    async def fail_model_run(self, run_id: str, *, error_code: str) -> None:
        async with self.session_factory() as session:
            run = await session.get(AIRun, run_id)
            if run is None:
                return
            run.status = "failed"
            run.error_code = error_code[:100]
            run.completed_at = datetime.now(timezone.utc)
            await session.commit()

    async def record_deterministic_summary(
        self,
        context: AIRunContext,
        *,
        content: str,
        reason: str | None = None,
    ) -> str:
        run = AIRun(
            id=str(uuid.uuid4()),
            user_id=context.user_id,
            item_id=context.item_id,
            analysis_version=context.analysis_version,
            job_id=context.job_id,
            workflow_id=context.workflow_id,
            correlation_id=context.correlation_id,
            task="summarization",
            provider="deterministic",
            requested_model=None,
            resolved_model=None,
            prompt_version="deterministic-summary-v1",
            schema_version=ENRICHMENT_SCHEMA_VERSION,
            content_hash=content_fingerprint(content),
            status="completed",
            completed_at=datetime.now(timezone.utc),
            attempts=0,
            fallback_chain=list(context.fallback_chain),
            error_code=reason[:100] if reason else None,
        )
        field = AIFieldProvenance(
            run_id=run.id,
            user_id=context.user_id,
            item_id=context.item_id,
            analysis_version=context.analysis_version,
            field_name="summary",
            source="deterministic",
            provider="deterministic",
            model=None,
        )
        async with self.session_factory() as session:
            session.add(run)
            await session.flush()
            session.add(field)
            await session.commit()
        return run.id
