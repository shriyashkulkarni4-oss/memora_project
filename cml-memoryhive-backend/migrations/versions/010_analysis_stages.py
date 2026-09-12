"""Persist durable Temporal analysis stage checkpoints.

Revision ID: 010
Revises: 009
Create Date: 2026-09-12 00:00:00
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "010"
down_revision: str | None = "009"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "processing_jobs",
        sa.Column("stage", sa.String(40), nullable=False, server_default="queued"),
    )
    op.add_column(
        "processing_jobs",
        sa.Column("stage_data", sa.JSON(), nullable=False, server_default="{}"),
    )
    op.add_column(
        "processing_jobs", sa.Column("content_hash", sa.String(64), nullable=True)
    )
    op.add_column(
        "processing_jobs",
        sa.Column("cancel_requested", sa.Boolean(), nullable=False, server_default="0"),
    )
    op.create_index(
        "ix_processing_jobs_temporal_stage",
        "processing_jobs",
        ["execution_backend", "stage", "updated_at"],
    )


def downgrade() -> None:
    op.drop_index("ix_processing_jobs_temporal_stage", table_name="processing_jobs")
    op.drop_column("processing_jobs", "cancel_requested")
    op.drop_column("processing_jobs", "content_hash")
    op.drop_column("processing_jobs", "stage_data")
    op.drop_column("processing_jobs", "stage")
