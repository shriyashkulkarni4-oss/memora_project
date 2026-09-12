"""Poll the database for pending item analysis and start Temporal workflows."""

import argparse
import asyncio
import hashlib
import logging
import signal
from dataclasses import dataclass

from sqlalchemy import select
from temporalio.client import Client

from app.config import get_settings
from app.database import async_session_maker
from app.models import AnalysisStatus, Item, ProcessingJob
from app.observability import (
    ANALYSIS_OUTCOMES,
    WORKER_POLL_TOTAL,
    mark_worker_heartbeat,
    start_component_metrics,
    update_queue_metrics,
)
from app.services.analysis_dispatch import backfill_pending_analysis
from app.temporal_pipeline.types import AnalysisWorkflowInput
from app.temporal_pipeline.workflows import AnalyzeItemWorkflow

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class PendingAnalysis:
    job_id: str
    item_id: str
    analysis_version: int
    item_type: str
    tenant_key: str
    provider: str
    model: str
    correlation_id: str


def workflow_id(item_id: str, analysis_version: int) -> str:
    return f"memoryhive-analysis-{item_id}-v{analysis_version}"


async def pending_analyses(limit: int) -> list[PendingAnalysis]:
    async with async_session_maker() as session:
        await backfill_pending_analysis(session, limit=limit)
        await session.commit()
        rows = (
            await session.execute(
                select(
                    ProcessingJob.id,
                    Item.id,
                    ProcessingJob.analysis_version,
                    Item.type,
                    Item.user_id,
                    ProcessingJob.ai_provider,
                    ProcessingJob.ai_model,
                    ProcessingJob.correlation_id,
                )
                .join(Item, ProcessingJob.item_id == Item.id)
                .where(
                    Item.deleted_at.is_(None),
                    ProcessingJob.execution_backend == "temporal",
                    ProcessingJob.status == "pending",
                    ProcessingJob.analysis_version == Item.analysis_version,
                )
                .order_by(
                    ProcessingJob.next_attempt_at.asc(),
                    ProcessingJob.created_at.asc(),
                    ProcessingJob.id.asc(),
                )
                .limit(limit)
            )
        ).all()
    return [
        PendingAnalysis(
            job_id=job_id,
            item_id=item_id,
            analysis_version=analysis_version,
            item_type=item_type,
            tenant_key=hashlib.sha256(user_id.encode("utf-8")).hexdigest()[:16],
            provider=ai_provider or "deterministic",
            model=ai_model or "none",
            correlation_id=correlation_id,
        )
        for (
            job_id,
            item_id,
            analysis_version,
            item_type,
            user_id,
            ai_provider,
            ai_model,
            correlation_id,
        ) in rows
        if analysis_version is not None
    ]


async def mark_workflow_scheduled(job_id: str, temporal_workflow_id: str) -> None:
    async with async_session_maker() as session:
        job = await session.get(ProcessingJob, job_id)
        if job is None or job.status != "pending":
            return
        item = await session.get(Item, job.item_id)
        job.status = "scheduled"
        job.temporal_workflow_id = temporal_workflow_id
        if item and item.analysis_status == AnalysisStatus.PENDING:
            item.analysis_status = AnalysisStatus.SCHEDULED
        await session.commit()


async def start_pending_workflows(client: Client, limit: int) -> int:
    started = 0
    for pending in await pending_analyses(limit):
        request = AnalysisWorkflowInput(
            job_id=pending.job_id,
            item_id=pending.item_id,
            analysis_version=pending.analysis_version,
            item_type=pending.item_type,
            tenant_key=pending.tenant_key,
            provider=pending.provider,
            model=pending.model,
            correlation_id=pending.correlation_id,
            search_attributes_enabled=(
                get_settings().temporal_custom_search_attributes_enabled
            ),
        )
        temporal_workflow_id = workflow_id(pending.item_id, pending.analysis_version)
        try:
            await client.start_workflow(
                AnalyzeItemWorkflow.run,
                request,
                id=temporal_workflow_id,
                task_queue=get_settings().temporal_task_queue,
                static_summary=f"Analyze Memoryhive {pending.item_type} item",
                static_details=(
                    f"analysis_version={pending.analysis_version}; "
                    f"tenant={pending.tenant_key}"
                ),
            )
            started += 1
        except Exception as exc:
            # Temporal raises WorkflowAlreadyStartedError for duplicates. Avoid
            # binding this scheduler to a narrow SDK exception import.
            if exc.__class__.__name__ != "WorkflowAlreadyStartedError":
                raise
        await mark_workflow_scheduled(pending.job_id, temporal_workflow_id)
        logger.info(
            "analysis workflow scheduled",
            extra={
                "correlation_id": pending.correlation_id,
                "job_id": pending.job_id,
                "workflow_id": temporal_workflow_id,
                "provider": pending.provider,
                "stage": "scheduled",
            },
        )
    return started


async def run_once(limit: int) -> int:
    settings = get_settings()
    mark_worker_heartbeat("temporal_scheduler")
    await update_queue_metrics(async_session_maker, backend="temporal")
    client = await Client.connect(
        settings.temporal_address,
        namespace=settings.temporal_namespace,
    )
    started = await start_pending_workflows(client, limit)
    WORKER_POLL_TOTAL.labels(
        "temporal_scheduler", "started" if started else "idle"
    ).inc()
    if started:
        ANALYSIS_OUTCOMES.labels("temporal", "scheduled", "started").inc(started)
    logger.info("Started %s item analysis workflow(s)", started)
    return started


async def run_forever(limit: int) -> None:
    settings = get_settings()
    stop = asyncio.Event()
    loop = asyncio.get_running_loop()
    for event in (signal.SIGINT, signal.SIGTERM):
        loop.add_signal_handler(event, stop.set)
    while not stop.is_set():
        await run_once(limit)
        try:
            await asyncio.wait_for(
                stop.wait(), settings.temporal_scheduler_poll_seconds
            )
        except TimeoutError:
            pass


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--once", action="store_true")
    parser.add_argument(
        "--limit", type=int, default=get_settings().temporal_scheduler_batch_size
    )
    args = parser.parse_args()
    start_component_metrics(
        get_settings().temporal_scheduler_metrics_port, "temporal_scheduler"
    )
    if args.once:
        asyncio.run(run_once(args.limit))
        return 0
    asyncio.run(run_forever(args.limit))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
