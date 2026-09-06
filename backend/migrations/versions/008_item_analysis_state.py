"""Add item analysis state for Temporal pipelines.

Revision ID: 008
Revises: 007
Create Date: 2026-09-06 00:00:00
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "008"
down_revision: str | None = "007"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "items",
        sa.Column(
            "analysis_status", sa.String(20), nullable=False, server_default="pending"
        ),
    )
    op.add_column("items", sa.Column("analysis_error", sa.Text(), nullable=True))
    op.add_column(
        "items",
        sa.Column("analysis_version", sa.Integer(), nullable=False, server_default="1"),
    )
    op.add_column(
        "items",
        sa.Column("analysis_requested_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "items",
        sa.Column("analysis_started_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "items",
        sa.Column("analysis_completed_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_items_analysis_status", "items", ["analysis_status"])


def downgrade() -> None:
    op.drop_index("ix_items_analysis_status", table_name="items")
    op.drop_column("items", "analysis_completed_at")
    op.drop_column("items", "analysis_started_at")
    op.drop_column("items", "analysis_requested_at")
    op.drop_column("items", "analysis_version")
    op.drop_column("items", "analysis_error")
    op.drop_column("items", "analysis_status")
