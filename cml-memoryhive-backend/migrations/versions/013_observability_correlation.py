"""Propagate bounded correlation metadata through analysis execution.

Revision ID: 013
Revises: 012
Create Date: 2026-09-12 00:00:00
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "013"
down_revision: str | None = "012"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "processing_jobs",
        sa.Column(
            "correlation_id",
            sa.String(128),
            nullable=False,
            server_default="legacy",
        ),
    )
    op.add_column("ai_runs", sa.Column("correlation_id", sa.String(128)))


def downgrade() -> None:
    op.drop_column("ai_runs", "correlation_id")
    op.drop_column("processing_jobs", "correlation_id")
