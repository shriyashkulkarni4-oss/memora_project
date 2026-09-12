"""Bounded-cardinality metrics for dispatch, workers, Temporal, and AI."""

import re
import time
from datetime import datetime, timedelta, timezone

from prometheus_client import Counter, Gauge, Histogram, start_http_server
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.config import Settings
from app.models import AnalysisStatus, Item, ProcessingJob

DISPATCH_TOTAL = Counter(
    "memoryhive_analysis_dispatch_total",
    "Analysis dispatch decisions",
    ("backend", "reason", "outcome"),
)
WORKER_POLL_TOTAL = Counter(
    "memoryhive_worker_poll_total",
    "Worker polls by bounded component and outcome",
    ("component", "outcome"),
)
WORKER_HEARTBEAT = Gauge(
    "memoryhive_worker_last_heartbeat_unixtime",
    "Last successful process-loop heartbeat",
    ("component",),
)
QUEUE_PENDING = Gauge(
    "memoryhive_analysis_queue_pending",
    "Pending analysis jobs",
    ("backend",),
)
QUEUE_OLDEST_AGE = Gauge(
    "memoryhive_analysis_queue_oldest_age_seconds",
    "Age of the oldest pending analysis job",
    ("backend",),
)
STUCK_ANALYSIS = Gauge(
    "memoryhive_analysis_stuck",
    "Items left analyzing beyond the bounded threshold",
    ("backend",),
)
ANALYSIS_OUTCOMES = Counter(
    "memoryhive_analysis_outcomes_total",
    "Analysis stage outcomes",
    ("backend", "stage", "outcome"),
)
ACTIVITY_DURATION = Histogram(
    "memoryhive_analysis_activity_duration_seconds",
    "Analysis activity duration",
    ("stage", "outcome"),
)
SCHEDULE_TO_START = Histogram(
    "memoryhive_analysis_schedule_to_start_seconds",
    "Time from dispatch creation to worker start",
    ("backend",),
)
AI_CALLS = Counter(
    "memoryhive_ai_calls_total",
    "AI invocation outcomes",
    ("provider", "model_alias", "task", "outcome"),
)
AI_LATENCY = Histogram(
    "memoryhive_ai_latency_seconds",
    "AI provider latency",
    ("provider", "model_alias", "task", "outcome"),
)
AI_FALLBACKS = Counter(
    "memoryhive_ai_fallback_total",
    "Configured gateway fallbacks used",
    ("provider", "model_alias", "task"),
)
AI_TOKENS = Counter(
    "memoryhive_ai_tokens_total",
    "Reported AI tokens",
    ("provider", "model_alias", "task", "direction"),
)
AI_COST = Counter(
    "memoryhive_ai_estimated_cost_usd_total",
    "Reported or estimated AI cost in USD",
    ("provider", "model_alias", "task"),
)
AI_CIRCUIT_OPEN = Gauge(
    "memoryhive_ai_circuit_open",
    "Whether the provider circuit is open",
    ("provider",),
)
SEARCH_REQUESTS = Counter(
    "memoryhive_search_requests_total",
    "Search requests by bounded retrieval mode and outcome",
    ("mode", "outcome"),
)
SEARCH_LATENCY = Histogram(
    "memoryhive_search_latency_seconds",
    "End-to-end search ranking latency",
    ("mode",),
)
SEARCH_SHADOW_OVERLAP = Histogram(
    "memoryhive_search_shadow_topk_overlap_ratio",
    "Top-k overlap between keyword control and shadow hybrid ranking",
    buckets=(0, 0.25, 0.5, 0.75, 0.9, 1.0),
)

BOUNDED_COMPONENTS = {"database_worker", "temporal_worker", "temporal_scheduler"}
BOUNDED_REASONS = {
    "capture",
    "content_updated",
    "manual_retry",
    "admin_retry",
    "backfill",
}


def safe_component(value: str) -> str:
    return value if value in BOUNDED_COMPONENTS else "other"


def safe_reason(value: str) -> str:
    return value if value in BOUNDED_REASONS else "other"


def configured_model_alias(settings: Settings, provider: str, model: str | None) -> str:
    """Return only operator-configured aliases; arbitrary model strings collapse."""
    configured = {
        value
        for value in (
            settings.ollama_model,
            settings.ollama_embedding_model,
            settings.openrouter_model,
            settings.openrouter_embedding_model,
            settings.huggingface_chat_model,
            settings.huggingface_embedding_model,
            settings.openai_compatible_model,
            settings.openai_compatible_embedding_model,
        )
        if value
    }
    configured.update(settings.openrouter_allowed_models)
    configured.update(settings.huggingface_chat_models)
    configured.update(settings.huggingface_embedding_models)
    configured.update(settings.huggingface_vision_models)
    configured.update(settings.openai_compatible_chat_models)
    configured.update(settings.openai_compatible_embedding_models)
    for task in ("summarization", "enrichment", "embeddings", "reranking", "vision"):
        routes = [
            getattr(settings, f"ai_{task}_route"),
            *getattr(settings, f"ai_{task}_fallback_routes"),
        ]
        for route in (value for value in routes if value):
            _provider, separator, configured_route_model = route.partition(":")
            if separator and configured_route_model:
                configured.add(configured_route_model)
    if not model:
        return "default"
    if model not in configured:
        return "other"
    normalized = re.sub(r"[^a-zA-Z0-9_.-]", "_", model)[:64]
    return normalized or f"{provider}_default"


def mark_worker_heartbeat(component: str) -> None:
    WORKER_HEARTBEAT.labels(safe_component(component)).set(time.time())


def start_component_metrics(port: int, component: str) -> None:
    start_http_server(port)
    mark_worker_heartbeat(component)


async def update_queue_metrics(
    session_factory: async_sessionmaker[AsyncSession], *, backend: str
) -> None:
    now = datetime.now(timezone.utc)
    async with session_factory() as session:
        pending = (
            await session.scalar(
                select(func.count())
                .select_from(ProcessingJob)
                .where(
                    ProcessingJob.execution_backend == backend,
                    ProcessingJob.status.in_(("pending", "scheduled")),
                )
            )
            or 0
        )
        oldest = await session.scalar(
            select(func.min(ProcessingJob.created_at)).where(
                ProcessingJob.execution_backend == backend,
                ProcessingJob.status.in_(("pending", "scheduled")),
            )
        )
        stuck = (
            await session.scalar(
                select(func.count())
                .select_from(Item)
                .join(
                    ProcessingJob,
                    (ProcessingJob.item_id == Item.id)
                    & (ProcessingJob.analysis_version == Item.analysis_version),
                )
                .where(
                    ProcessingJob.execution_backend == backend,
                    Item.analysis_status == AnalysisStatus.ANALYZING.value,
                    Item.analysis_started_at < now - timedelta(minutes=10),
                )
            )
            or 0
        )
    QUEUE_PENDING.labels(backend).set(pending)
    if oldest:
        if oldest.tzinfo is None:
            oldest = oldest.replace(tzinfo=timezone.utc)
        QUEUE_OLDEST_AGE.labels(backend).set(max(0, (now - oldest).total_seconds()))
    else:
        QUEUE_OLDEST_AGE.labels(backend).set(0)
    STUCK_ANALYSIS.labels(backend).set(stuck)
