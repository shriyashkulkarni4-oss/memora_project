"""Temporal workflow execution and replay regression tests."""

import asyncio
import uuid

import pytest
from temporalio import activity
from temporalio.testing import WorkflowEnvironment
from temporalio.worker import Replayer, Worker

from app.services.analysis import AnalysisOutcome
from app.temporal_pipeline.types import (
    AnalysisStageOutcome,
    AnalysisWorkflowInput,
    BackfillWorkflowInput,
    EmbeddingBackfillInput,
    EmbeddingBackfillPageInput,
    EmbeddingBackfillPageOutcome,
)
from app.temporal_pipeline.workflows import (
    AnalyzeItemWorkflow,
    BackfillAnalysisWorkflow,
    BackfillEmbeddingsWorkflow,
)

pytestmark = pytest.mark.asyncio

executed_stages: list[str] = []


def stage_activity(name: str, result_stage: str):
    @activity.defn(name=name)
    async def run(request: AnalysisWorkflowInput) -> AnalysisStageOutcome:
        executed_stages.append(result_stage)
        return AnalysisStageOutcome(
            request.item_id, request.analysis_version, result_stage, "hash"
        )

    return run


fake_extract = stage_activity("extract_item_activity", "extracted")
fake_enrich = stage_activity("enrich_item_activity", "enriched")
fake_embed = stage_activity("embed_item_activity", "embedded")
fake_index = stage_activity("index_item_activity", "completed")


@activity.defn(name="persist_analysis_activity")
async def fake_persist(request: AnalysisWorkflowInput) -> AnalysisOutcome:
    executed_stages.append("persisted")
    return AnalysisOutcome(request.item_id, "analyzed", request.analysis_version)


@activity.defn(name="finalize_analysis_failure_activity")
async def fake_failure(_request: AnalysisWorkflowInput, _error: str) -> None:
    executed_stages.append("failed")


@activity.defn(name="finalize_analysis_cancellation_activity")
async def fake_cancellation(_request: AnalysisWorkflowInput) -> None:
    executed_stages.append("cancelled")


@activity.defn(name="analyze_item_activity")
async def fake_legacy(request: AnalysisWorkflowInput) -> AnalysisOutcome:
    executed_stages.append("legacy")
    return AnalysisOutcome(request.item_id, "analyzed", request.analysis_version)


@activity.defn(name="backfill_embeddings_activity")
async def fake_embedding_backfill(
    request: EmbeddingBackfillPageInput,
) -> EmbeddingBackfillPageOutcome:
    executed_stages.append(f"embedding-page:{request.cursor or 'start'}")
    if request.cursor is None:
        return EmbeddingBackfillPageOutcome(1, "item-1", False)
    return EmbeddingBackfillPageOutcome(1, None, True)


FAKE_ACTIVITIES = [
    fake_extract,
    fake_enrich,
    fake_embed,
    fake_persist,
    fake_index,
    fake_failure,
    fake_cancellation,
    fake_legacy,
]

extract_started: asyncio.Event | None = None
release_extract: asyncio.Event | None = None


@activity.defn(name="extract_item_activity")
async def controlled_extract(request: AnalysisWorkflowInput) -> AnalysisStageOutcome:
    assert extract_started is not None and release_extract is not None
    extract_started.set()
    await release_extract.wait()
    executed_stages.append("extracted")
    return AnalysisStageOutcome(request.item_id, request.analysis_version, "extracted")


async def test_multistage_workflow_executes_in_order_and_replays() -> None:
    executed_stages.clear()
    environment = await WorkflowEnvironment.start_time_skipping()
    task_queue = f"analysis-test-{uuid.uuid4()}"
    request = AnalysisWorkflowInput("job-1", "item-1", 1, item_type="text")
    try:
        async with Worker(
            environment.client,
            task_queue=task_queue,
            workflows=[AnalyzeItemWorkflow],
            activities=FAKE_ACTIVITIES,
        ):
            handle = await environment.client.start_workflow(
                AnalyzeItemWorkflow.run,
                request,
                id=f"analysis-{uuid.uuid4()}",
                task_queue=task_queue,
            )
            result = await handle.result()
            history = await handle.fetch_history()

        assert result.status == "analyzed"
        assert executed_stages == [
            "extracted",
            "enriched",
            "embedded",
            "persisted",
            "completed",
        ]
        replay = await Replayer(workflows=[AnalyzeItemWorkflow]).replay_workflow(
            history
        )
        assert replay.replay_failure is None
    finally:
        await environment.shutdown()


async def test_backfill_workflow_runs_bounded_children() -> None:
    executed_stages.clear()
    environment = await WorkflowEnvironment.start_time_skipping()
    task_queue = f"backfill-test-{uuid.uuid4()}"
    requests = tuple(
        AnalysisWorkflowInput(f"job-{index}", f"item-{index}", 1, item_type="text")
        for index in range(2)
    )
    try:
        async with Worker(
            environment.client,
            task_queue=task_queue,
            workflows=[AnalyzeItemWorkflow, BackfillAnalysisWorkflow],
            activities=FAKE_ACTIVITIES,
        ):
            result = await environment.client.execute_workflow(
                BackfillAnalysisWorkflow.run,
                BackfillWorkflowInput(requests=requests, items_per_minute=1),
                id=f"backfill-{uuid.uuid4()}",
                task_queue=task_queue,
            )

        assert result.total == 2
        assert result.completed == 2
        assert result.cancelled is False
        assert executed_stages.count("extracted") == 2
    finally:
        await environment.shutdown()


async def test_embedding_backfill_workflow_persists_cursor_and_rate_limits() -> None:
    executed_stages.clear()
    environment = await WorkflowEnvironment.start_time_skipping()
    task_queue = f"embedding-backfill-test-{uuid.uuid4()}"
    try:
        async with Worker(
            environment.client,
            task_queue=task_queue,
            workflows=[BackfillEmbeddingsWorkflow],
            activities=[fake_embedding_backfill],
        ):
            result = await environment.client.execute_workflow(
                BackfillEmbeddingsWorkflow.run,
                EmbeddingBackfillInput(
                    expected_index_version=2,
                    max_items=2,
                    items_per_minute=1,
                ),
                id=f"embedding-backfill-{uuid.uuid4()}",
                task_queue=task_queue,
            )

        assert result.completed == 2
        assert result.exhausted is True
        assert executed_stages == ["embedding-page:start", "embedding-page:item-1"]
    finally:
        await environment.shutdown()


async def test_cancel_signal_stops_after_current_idempotent_stage() -> None:
    global extract_started, release_extract
    executed_stages.clear()
    extract_started = asyncio.Event()
    release_extract = asyncio.Event()
    environment = await WorkflowEnvironment.start_time_skipping()
    task_queue = f"cancel-test-{uuid.uuid4()}"
    request = AnalysisWorkflowInput("job-cancel", "item-cancel", 1)
    activities = [
        controlled_extract,
        fake_enrich,
        fake_embed,
        fake_persist,
        fake_index,
        fake_failure,
        fake_cancellation,
        fake_legacy,
    ]
    try:
        async with Worker(
            environment.client,
            task_queue=task_queue,
            workflows=[AnalyzeItemWorkflow],
            activities=activities,
        ):
            handle = await environment.client.start_workflow(
                AnalyzeItemWorkflow.run,
                request,
                id=f"cancel-{uuid.uuid4()}",
                task_queue=task_queue,
            )
            await extract_started.wait()
            await handle.signal(AnalyzeItemWorkflow.request_cancel)
            release_extract.set()
            result = await handle.result()

        assert result.status == "cancelled"
        assert executed_stages == ["extracted", "cancelled"]
    finally:
        await environment.shutdown()
