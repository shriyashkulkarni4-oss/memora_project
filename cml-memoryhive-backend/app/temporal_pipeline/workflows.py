"""Temporal workflows for durable item analysis."""

from datetime import timedelta

from temporalio import workflow
from temporalio.common import RetryPolicy

with workflow.unsafe.imports_passed_through():
    from app.temporal_pipeline.activities import analyze_item_activity
    from app.temporal_pipeline.types import AnalysisWorkflowInput


@workflow.defn
class AnalyzeItemWorkflow:
    @workflow.run
    async def run(self, request: AnalysisWorkflowInput) -> object:
        return await workflow.execute_activity(
            analyze_item_activity,
            request,
            start_to_close_timeout=timedelta(minutes=10),
            retry_policy=RetryPolicy(
                initial_interval=timedelta(seconds=5),
                maximum_interval=timedelta(minutes=2),
                maximum_attempts=3,
            ),
        )
