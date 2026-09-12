"""Temporal worker process for Memoryhive item analysis workflows."""

import asyncio
import logging

from temporalio.client import Client
from temporalio.runtime import PrometheusConfig, Runtime, TelemetryConfig
from temporalio.worker import Worker

from app.config import get_settings
from app.observability import mark_worker_heartbeat, start_component_metrics
from app.temporal_pipeline.activities import (
    analyze_item_activity,
    backfill_embeddings_activity,
    embed_item_activity,
    enrich_item_activity,
    extract_item_activity,
    finalize_analysis_cancellation_activity,
    finalize_analysis_failure_activity,
    index_item_activity,
    persist_analysis_activity,
)
from app.temporal_pipeline.workflows import (
    AnalyzeItemWorkflow,
    BackfillAnalysisWorkflow,
    BackfillEmbeddingsWorkflow,
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def run() -> None:
    settings = get_settings()
    start_component_metrics(settings.temporal_worker_metrics_port, "temporal_worker")
    runtime = Runtime(
        telemetry=TelemetryConfig(
            metrics=PrometheusConfig(
                f"0.0.0.0:{settings.temporal_sdk_metrics_port}",
                counters_total_suffix=True,
                durations_as_seconds=True,
            ),
            metric_prefix="temporal_sdk_",
        )
    )
    client = await Client.connect(
        settings.temporal_address,
        namespace=settings.temporal_namespace,
        runtime=runtime,
    )
    if settings.temporal_payload_encryption_required and not getattr(
        client.data_converter, "payload_codec", None
    ):
        raise RuntimeError(
            "Temporal payload encryption is required but no payload codec is configured"
        )
    worker = Worker(
        client,
        task_queue=settings.temporal_task_queue,
        workflows=[
            AnalyzeItemWorkflow,
            BackfillAnalysisWorkflow,
            BackfillEmbeddingsWorkflow,
        ],
        activities=[
            analyze_item_activity,
            backfill_embeddings_activity,
            extract_item_activity,
            enrich_item_activity,
            embed_item_activity,
            persist_analysis_activity,
            index_item_activity,
            finalize_analysis_failure_activity,
            finalize_analysis_cancellation_activity,
        ],
        build_id=settings.temporal_worker_build_id,
    )
    logger.info(
        "Temporal worker started on %s/%s",
        settings.temporal_namespace,
        settings.temporal_task_queue,
    )

    async def heartbeat() -> None:
        while True:
            mark_worker_heartbeat("temporal_worker")
            await asyncio.sleep(15)

    heartbeat_task = asyncio.create_task(heartbeat())
    try:
        await worker.run()
    finally:
        heartbeat_task.cancel()


if __name__ == "__main__":
    asyncio.run(run())
