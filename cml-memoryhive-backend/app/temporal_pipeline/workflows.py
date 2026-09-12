"""Versioned Temporal workflows for durable item analysis and backfills."""

from datetime import timedelta

from temporalio import workflow
from temporalio.common import RetryPolicy, SearchAttributeKey
from temporalio.exceptions import ActivityError

with workflow.unsafe.imports_passed_through():
    from app.services.analysis import AnalysisOutcome
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
    from app.temporal_pipeline.types import (
        AnalysisWorkflowInput,
        BackfillWorkflowInput,
        BackfillWorkflowOutcome,
        EmbeddingBackfillInput,
        EmbeddingBackfillOutcome,
        EmbeddingBackfillPageInput,
    )


EXTRACTION_RETRY = RetryPolicy(
    initial_interval=timedelta(seconds=5),
    maximum_interval=timedelta(minutes=2),
    maximum_attempts=3,
)
ENRICHMENT_RETRY = RetryPolicy(
    initial_interval=timedelta(seconds=10),
    maximum_interval=timedelta(minutes=3),
    maximum_attempts=4,
)
PERSISTENCE_RETRY = RetryPolicy(
    initial_interval=timedelta(seconds=2),
    maximum_interval=timedelta(seconds=30),
    maximum_attempts=5,
)

ITEM_TYPE_KEY = SearchAttributeKey.for_keyword("MemoryhiveItemType")
TENANT_KEY = SearchAttributeKey.for_keyword("MemoryhiveTenant")
VERSION_KEY = SearchAttributeKey.for_int("MemoryhiveAnalysisVersion")
PROVIDER_KEY = SearchAttributeKey.for_keyword("MemoryhiveProvider")
MODEL_KEY = SearchAttributeKey.for_keyword("MemoryhiveModel")
STAGE_KEY = SearchAttributeKey.for_keyword("MemoryhiveStage")
OUTCOME_KEY = SearchAttributeKey.for_keyword("MemoryhiveOutcome")


@workflow.defn
class AnalyzeItemWorkflow:
    def __init__(self) -> None:
        self.cancel_requested = False
        self.stage = "queued"

    @workflow.signal
    def request_cancel(self) -> None:
        self.cancel_requested = True

    @workflow.query
    def current_stage(self) -> str:
        return self.stage

    def _set_stage(
        self,
        request: AnalysisWorkflowInput,
        stage: str,
        *,
        outcome: str | None = None,
    ) -> None:
        self.stage = stage
        if not request.search_attributes_enabled:
            return
        updates = [STAGE_KEY.value_set(stage)]
        if outcome:
            updates.append(OUTCOME_KEY.value_set(outcome))
        workflow.upsert_search_attributes(updates)

    async def _cancel_if_requested(self, request: AnalysisWorkflowInput) -> bool:
        if not self.cancel_requested:
            return False
        self._set_stage(request, "cancelled", outcome="cancelled")
        await workflow.execute_activity(
            finalize_analysis_cancellation_activity,
            request,
            start_to_close_timeout=timedelta(minutes=1),
            retry_policy=PERSISTENCE_RETRY,
        )
        return True

    @workflow.run
    async def run(self, request: AnalysisWorkflowInput) -> AnalysisOutcome:
        # Preserve replay compatibility for histories started by the original
        # one-activity workflow while all new executions use stage checkpoints.
        if not workflow.patched("analysis-multistage-v1"):
            return await workflow.execute_activity(
                analyze_item_activity,
                request,
                start_to_close_timeout=timedelta(minutes=10),
                retry_policy=EXTRACTION_RETRY,
            )

        if request.search_attributes_enabled:
            workflow.upsert_search_attributes(
                [
                    ITEM_TYPE_KEY.value_set(request.item_type),
                    TENANT_KEY.value_set(request.tenant_key),
                    VERSION_KEY.value_set(request.analysis_version),
                    PROVIDER_KEY.value_set(request.provider),
                    MODEL_KEY.value_set(request.model),
                    OUTCOME_KEY.value_set("running"),
                ]
            )
        try:
            self._set_stage(request, "extracting")
            await workflow.execute_activity(
                extract_item_activity,
                request,
                start_to_close_timeout=timedelta(minutes=10),
                heartbeat_timeout=timedelta(minutes=1),
                retry_policy=EXTRACTION_RETRY,
                summary="Acquire and extract item content",
            )
            if await self._cancel_if_requested(request):
                return AnalysisOutcome(
                    request.item_id, "cancelled", request.analysis_version
                )

            self._set_stage(request, "enriching")
            await workflow.execute_activity(
                enrich_item_activity,
                request,
                start_to_close_timeout=timedelta(minutes=3),
                retry_policy=ENRICHMENT_RETRY,
                summary="Generate structured AI enrichment",
            )
            if await self._cancel_if_requested(request):
                return AnalysisOutcome(
                    request.item_id, "cancelled", request.analysis_version
                )

            self._set_stage(request, "embedding")
            await workflow.execute_activity(
                embed_item_activity,
                request,
                start_to_close_timeout=timedelta(minutes=5),
                heartbeat_timeout=timedelta(minutes=1),
                retry_policy=ENRICHMENT_RETRY,
                summary="Chunk and embed extracted content",
            )
            if await self._cancel_if_requested(request):
                return AnalysisOutcome(
                    request.item_id, "cancelled", request.analysis_version
                )

            self._set_stage(request, "persisting")
            outcome = await workflow.execute_activity(
                persist_analysis_activity,
                request,
                start_to_close_timeout=timedelta(minutes=2),
                retry_policy=PERSISTENCE_RETRY,
                summary="Persist the versioned analysis result",
            )
            if await self._cancel_if_requested(request):
                return AnalysisOutcome(
                    request.item_id, "cancelled", request.analysis_version
                )
            self._set_stage(request, "indexing")
            await workflow.execute_activity(
                index_item_activity,
                request,
                start_to_close_timeout=timedelta(minutes=2),
                retry_policy=PERSISTENCE_RETRY,
                summary="Publish item to retrieval indexes",
            )
            self._set_stage(request, "completed", outcome="completed")
            return outcome
        except ActivityError as exc:
            self._set_stage(request, "failed", outcome="failed")
            await workflow.execute_activity(
                finalize_analysis_failure_activity,
                args=[request, str(exc)[:4000]],
                start_to_close_timeout=timedelta(minutes=1),
                retry_policy=PERSISTENCE_RETRY,
            )
            raise


@workflow.defn
class BackfillAnalysisWorkflow:
    def __init__(self) -> None:
        self.paused = False
        self.cancelled = False
        self.completed = 0

    @workflow.signal
    def pause(self) -> None:
        self.paused = True

    @workflow.signal
    def resume(self) -> None:
        self.paused = False

    @workflow.signal
    def cancel(self) -> None:
        self.cancelled = True
        self.paused = False

    @workflow.query
    def progress(self) -> dict[str, int | bool]:
        return {
            "completed": self.completed,
            "paused": self.paused,
            "cancelled": self.cancelled,
        }

    @workflow.run
    async def run(self, request: BackfillWorkflowInput) -> BackfillWorkflowOutcome:
        rate = max(1, request.items_per_minute)
        interval = timedelta(seconds=60 / rate)
        for child_request in request.requests:
            await workflow.wait_condition(lambda: not self.paused or self.cancelled)
            if self.cancelled:
                break
            await workflow.execute_child_workflow(
                AnalyzeItemWorkflow.run,
                child_request,
                id=(
                    f"memoryhive-analysis-{child_request.item_id}"
                    f"-v{child_request.analysis_version}"
                ),
                retry_policy=RetryPolicy(maximum_attempts=1),
                static_summary="Memoryhive analysis backfill item",
            )
            self.completed += 1
            if self.completed < len(request.requests):
                await workflow.sleep(interval)
        return BackfillWorkflowOutcome(
            total=len(request.requests),
            completed=self.completed,
            cancelled=self.cancelled,
        )


@workflow.defn
class BackfillEmbeddingsWorkflow:
    def __init__(self) -> None:
        self.completed = 0
        self.cursor: str | None = None

    @workflow.query
    def progress(self) -> dict[str, int | str | None]:
        return {"completed": self.completed, "cursor": self.cursor}

    @workflow.run
    async def run(self, request: EmbeddingBackfillInput) -> EmbeddingBackfillOutcome:
        self.cursor = request.cursor
        exhausted = False
        rate = max(1, request.items_per_minute)
        page_limit = min(25, rate)
        while self.completed < max(0, request.max_items) and not exhausted:
            remaining = request.max_items - self.completed
            page = await workflow.execute_activity(
                backfill_embeddings_activity,
                EmbeddingBackfillPageInput(
                    expected_index_version=request.expected_index_version,
                    cursor=self.cursor,
                    limit=min(page_limit, remaining),
                ),
                start_to_close_timeout=timedelta(minutes=15),
                heartbeat_timeout=timedelta(minutes=1),
                retry_policy=ENRICHMENT_RETRY,
                summary="Backfill one bounded embedding page",
            )
            self.completed += page.processed
            self.cursor = page.next_cursor
            exhausted = page.exhausted
            if not exhausted and self.completed < request.max_items:
                await workflow.sleep(
                    timedelta(seconds=(60 * max(1, page.processed)) / rate)
                )
        return EmbeddingBackfillOutcome(
            completed=self.completed,
            cursor=self.cursor,
            exhausted=exhausted,
        )
