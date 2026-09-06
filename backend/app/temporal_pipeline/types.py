"""Serializable payloads used by Temporal workflows and activities."""

from dataclasses import dataclass


@dataclass(frozen=True)
class AnalysisWorkflowInput:
    item_id: str
    analysis_version: int
