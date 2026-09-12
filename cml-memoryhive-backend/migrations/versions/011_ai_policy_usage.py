"""Capture AI routing policy and usage reservations.

Revision ID: 011
Revises: 010
Create Date: 2026-09-12 00:00:00
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "011"
down_revision: str | None = "010"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("processing_jobs", sa.Column("ai_provider", sa.String(40)))
    op.add_column("processing_jobs", sa.Column("ai_model", sa.String(255)))
    op.add_column(
        "processing_jobs",
        sa.Column("ai_policy", sa.JSON(), nullable=False, server_default="{}"),
    )
    op.create_table(
        "ai_usage_events",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("operation_key", sa.String(255), nullable=False, unique=True),
        sa.Column(
            "user_id", sa.String(36), sa.ForeignKey("users.id", ondelete="SET NULL")
        ),
        sa.Column(
            "item_id", sa.String(36), sa.ForeignKey("items.id", ondelete="SET NULL")
        ),
        sa.Column("task", sa.String(40), nullable=False),
        sa.Column("provider", sa.String(40), nullable=False),
        sa.Column("model", sa.String(255)),
        sa.Column("status", sa.String(20), nullable=False, server_default="reserved"),
        sa.Column("input_tokens", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("output_tokens", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("total_tokens", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("cost_usd", sa.Float(), nullable=False, server_default="0"),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column("completed_at", sa.DateTime(timezone=True)),
    )
    op.create_index("ix_ai_usage_created", "ai_usage_events", ["created_at"])
    op.create_index(
        "ix_ai_usage_user_created", "ai_usage_events", ["user_id", "created_at"]
    )


def downgrade() -> None:
    op.drop_index("ix_ai_usage_user_created", table_name="ai_usage_events")
    op.drop_index("ix_ai_usage_created", table_name="ai_usage_events")
    op.drop_table("ai_usage_events")
    op.drop_column("processing_jobs", "ai_policy")
    op.drop_column("processing_jobs", "ai_model")
    op.drop_column("processing_jobs", "ai_provider")
