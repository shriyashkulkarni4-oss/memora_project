"""Add private item interaction events for explainable memory ranking.

Revision ID: 018
Revises: 017
Create Date: 2026-09-12 00:00:00
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "018"
down_revision: str | None = "017"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "item_interactions",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column(
            "user_id",
            sa.String(36),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "subject_item_id",
            sa.String(36),
            sa.ForeignKey("items.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "context_item_id",
            sa.String(36),
            sa.ForeignKey("items.id", ondelete="CASCADE"),
        ),
        sa.Column("kind", sa.String(30), nullable=False),
        sa.Column("action", sa.String(30), nullable=False),
        sa.Column("client_id", sa.String(100)),
        sa.Column(
            "reverses_id",
            sa.String(36),
            sa.ForeignKey("item_interactions.id", ondelete="SET NULL"),
        ),
        sa.Column("reason_code", sa.String(60)),
        sa.Column("metadata", sa.JSON()),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.UniqueConstraint("user_id", "client_id", name="uq_item_interaction_client"),
    )
    op.create_index(
        "ix_item_interaction_subject_created",
        "item_interactions",
        ["user_id", "subject_item_id", "created_at"],
    )
    op.create_index(
        "ix_item_interaction_kind_action",
        "item_interactions",
        ["user_id", "kind", "action"],
    )


def downgrade() -> None:
    op.drop_index("ix_item_interaction_kind_action", table_name="item_interactions")
    op.drop_index("ix_item_interaction_subject_created", table_name="item_interactions")
    op.drop_table("item_interactions")
