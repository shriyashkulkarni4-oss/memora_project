"""Temporal worker process for Memoryhive item analysis workflows."""

import asyncio
import logging

from temporalio.client import Client
from temporalio.worker import Worker

from app.config import get_settings
from app.temporal_pipeline.activities import analyze_item_activity
from app.temporal_pipeline.workflows import AnalyzeItemWorkflow

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def run() -> None:
    settings = get_settings()
    client = await Client.connect(
        settings.temporal_address,
        namespace=settings.temporal_namespace,
    )
    worker = Worker(
        client,
        task_queue=settings.temporal_task_queue,
        workflows=[AnalyzeItemWorkflow],
        activities=[analyze_item_activity],
    )
    logger.info(
        "Temporal worker started on %s/%s",
        settings.temporal_namespace,
        settings.temporal_task_queue,
    )
    await worker.run()


if __name__ == "__main__":
    asyncio.run(run())
