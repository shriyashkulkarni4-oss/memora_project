"""Temporal activities for item analysis."""

from temporalio import activity

from app.config import get_settings
from app.database import async_session_maker
from app.services.analysis import AnalysisOutcome, run_item_analysis
from app.services.processing import ContentProcessor
from app.services.storage import get_storage_service
from app.temporal_pipeline.types import AnalysisWorkflowInput


@activity.defn
async def analyze_item_activity(request: AnalysisWorkflowInput) -> AnalysisOutcome:
    settings = get_settings()
    processor = ContentProcessor(get_storage_service(), settings)
    return await run_item_analysis(
        async_session_maker,
        processor,
        request.item_id,
        request.analysis_version,
    )
