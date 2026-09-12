"""Add auditable admin analysis operations.

Revision ID: 014
Revises: 013
Create Date: 2026-09-12 00:00:00
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "014"
down_revision: str | None = "013"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "admin_analysis_actions",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column(
            "actor_user_id",
            sa.String(36),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
        ),
        sa.Column(
            "item_id",
            sa.String(36),
            sa.ForeignKey("items.id", ondelete="SET NULL"),
        ),
        sa.Column(
            "job_id",
            sa.String(36),
            sa.ForeignKey("processing_jobs.id", ondelete="SET NULL"),
        ),
        sa.Column("action", sa.String(20), nullable=False),
        sa.Column("status", sa.String(20), nullable=False),
        sa.Column("idempotency_key", sa.String(255), nullable=False),
        sa.Column("correlation_id", sa.String(128), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.UniqueConstraint("idempotency_key", name="uq_admin_analysis_action_key"),
    )
    op.create_index(
        "ix_admin_analysis_actions_created",
        "admin_analysis_actions",
        ["created_at"],
    )
    op.create_index(
        "ix_admin_analysis_actions_job", "admin_analysis_actions", ["job_id"]
    )


def downgrade() -> None:
    op.drop_index("ix_admin_analysis_actions_job", table_name="admin_analysis_actions")
    op.drop_index(
        "ix_admin_analysis_actions_created", table_name="admin_analysis_actions"
    )
    op.drop_table("admin_analysis_actions")
