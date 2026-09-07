"""Poll the database for pending item analysis and start Temporal workflows."""

import argparse
import asyncio
import logging
import signal
from dataclasses import dataclass

from sqlalchemy import select
from temporalio.client import Client

from app.config import get_settings
from app.database import async_session_maker
from app.models import AnalysisStatus, Item
from app.temporal_pipeline.types import AnalysisWorkflowInput
from app.temporal_pipeline.workflows import AnalyzeItemWorkflow

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class PendingAnalysis:
    item_id: str
    analysis_version: int


def workflow_id(item_id: str, analysis_version: int) -> str:
    return f"memoryhive-analysis-{item_id}-v{analysis_version}"


async def pending_analyses(limit: int) -> list[PendingAnalysis]:
    async with async_session_maker() as session:
        rows = (
            await session.execute(
                select(Item.id, Item.analysis_version)
                .where(
                    Item.deleted_at.is_(None),
                    Item.analysis_status == AnalysisStatus.PENDING.value,
                )
                .order_by(
                    Item.analysis_requested_at.asc().nullsfirst(),
                    Item.created_at.asc(),
                    Item.id.asc(),
                )
                .limit(limit)
            )
        ).all()
    return [
        PendingAnalysis(item_id=item_id, analysis_version=analysis_version)
        for item_id, analysis_version in rows
    ]


async def start_pending_workflows(client: Client, limit: int) -> int:
    started = 0
    for pending in await pending_analyses(limit):
        request = AnalysisWorkflowInput(
            item_id=pending.item_id,
            analysis_version=pending.analysis_version,
        )
        try:
            await client.start_workflow(
                AnalyzeItemWorkflow.run,
                request,
                id=workflow_id(pending.item_id, pending.analysis_version),
                task_queue=get_settings().temporal_task_queue,
            )
            started += 1
        except Exception as exc:
            # Temporal raises WorkflowAlreadyStartedError for duplicates. Avoid
            # binding this scheduler to a narrow SDK exception import.
            if exc.__class__.__name__ != "WorkflowAlreadyStartedError":
                raise
    return started


async def run_once(limit: int) -> int:
    settings = get_settings()
    client = await Client.connect(
        settings.temporal_address,
        namespace=settings.temporal_namespace,
    )
    started = await start_pending_workflows(client, limit)
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
    if args.once:
        asyncio.run(run_once(args.limit))
        return 0
    asyncio.run(run_forever(args.limit))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
