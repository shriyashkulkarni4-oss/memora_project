"""Add versioned structured enrichment records.

Revision ID: 015
Revises: 014
Create Date: 2026-09-12 00:00:00
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "015"
down_revision: str | None = "014"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "enrichment_records",
        sa.Column("id", sa.String(36), primary_key=True),
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
            "ai_run_id",
            sa.String(36),
            sa.ForeignKey("ai_runs.id", ondelete="SET NULL"),
        ),
        sa.Column("analysis_version", sa.Integer(), nullable=False),
        sa.Column("schema_version", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("taxonomy_version", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("summary", sa.Text()),
        sa.Column("detailed_summary", sa.Text()),
        sa.Column("topics", sa.JSON(), nullable=False, server_default="[]"),
        sa.Column("suggested_tags", sa.JSON(), nullable=False, server_default="[]"),
        sa.Column("classification", sa.String(100)),
        sa.Column("entities", sa.JSON(), nullable=False, server_default="[]"),
        sa.Column("key_phrases", sa.JSON(), nullable=False, server_default="[]"),
        sa.Column("content_language", sa.String(20)),
        sa.Column("confidence", sa.Float()),
        sa.Column("warnings", sa.JSON(), nullable=False, server_default="[]"),
        sa.Column("provider", sa.String(40), nullable=False),
        sa.Column("model", sa.String(255)),
        sa.Column("prompt_version", sa.String(40), nullable=False),
        sa.Column("content_hash", sa.String(64), nullable=False),
        sa.Column("field_provenance", sa.JSON(), nullable=False, server_default="{}"),
        sa.Column(
            "generated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.UniqueConstraint(
            "item_id", "analysis_version", name="uq_enrichment_item_version"
        ),
    )
    op.create_index(
        "ix_enrichment_user_generated",
        "enrichment_records",
        ["user_id", "generated_at"],
    )
    op.create_index(
        "ix_enrichment_classification", "enrichment_records", ["classification"]
    )


def downgrade() -> None:
    op.drop_index("ix_enrichment_classification", table_name="enrichment_records")
    op.drop_index("ix_enrichment_user_generated", table_name="enrichment_records")
    op.drop_table("enrichment_records")
