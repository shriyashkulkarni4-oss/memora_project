"""Add private reversible AI suggestion feedback.

Revision ID: 016
Revises: 015
Create Date: 2026-09-12 00:00:00
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "016"
down_revision: str | None = "015"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "ai_suggestion_feedback",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("client_id", sa.String(100), nullable=False),
        sa.Column(
            "user_id",
            sa.String(36),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "item_id",
            sa.String(36),
            sa.ForeignKey("items.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "enrichment_id",
            sa.String(36),
            sa.ForeignKey("enrichment_records.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("analysis_version", sa.Integer(), nullable=False),
        sa.Column("suggestion_type", sa.String(30), nullable=False),
        sa.Column("value", sa.String(100), nullable=False),
        sa.Column("normalized_value", sa.String(100), nullable=False),
        sa.Column("action", sa.String(30), nullable=False),
        sa.Column(
            "changed_item", sa.Boolean(), nullable=False, server_default=sa.false()
        ),
        sa.Column("item_revision_after", sa.Integer(), nullable=False),
        sa.Column("metadata", sa.JSON(), nullable=False, server_default="{}"),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.UniqueConstraint("client_id", name="uq_ai_suggestion_feedback_client"),
    )
    op.create_index(
        "ix_ai_suggestion_item_version",
        "ai_suggestion_feedback",
        ["item_id", "analysis_version"],
    )
    op.create_index(
        "ix_ai_suggestion_user_created",
        "ai_suggestion_feedback",
        ["user_id", "created_at"],
    )
    op.create_table(
        "ai_suggestion_preferences",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column(
            "user_id",
            sa.String(36),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("suggestion_type", sa.String(30), nullable=False),
        sa.Column("normalized_value", sa.String(100), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.UniqueConstraint(
            "user_id",
            "suggestion_type",
            "normalized_value",
            name="uq_ai_suggestion_preference",
        ),
    )


def downgrade() -> None:
    op.drop_table("ai_suggestion_preferences")
    op.drop_index("ix_ai_suggestion_user_created", table_name="ai_suggestion_feedback")
    op.drop_index("ix_ai_suggestion_item_version", table_name="ai_suggestion_feedback")
    op.drop_table("ai_suggestion_feedback")
