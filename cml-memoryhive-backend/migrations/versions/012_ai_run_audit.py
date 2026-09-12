"""Add privacy-safe AI run, field provenance, and embedding records.

Revision ID: 012
Revises: 011
Create Date: 2026-09-12 00:00:00
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "012"
down_revision: str | None = "011"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "ai_runs",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column(
            "user_id",
            sa.String(36),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
        ),
        sa.Column(
            "item_id",
            sa.String(36),
            sa.ForeignKey("items.id", ondelete="CASCADE"),
        ),
        sa.Column("analysis_version", sa.Integer()),
        sa.Column(
            "job_id",
            sa.String(36),
            sa.ForeignKey("processing_jobs.id", ondelete="SET NULL"),
        ),
        sa.Column("workflow_id", sa.String(255)),
        sa.Column("task", sa.String(40), nullable=False),
        sa.Column("provider", sa.String(40), nullable=False),
        sa.Column("requested_model", sa.String(255)),
        sa.Column("resolved_model", sa.String(255)),
        sa.Column(
            "prompt_version",
            sa.String(40),
            nullable=False,
            server_default="enrichment-v1",
        ),
        sa.Column("schema_version", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("content_hash", sa.String(64), nullable=False),
        sa.Column("status", sa.String(30), nullable=False, server_default="started"),
        sa.Column(
            "started_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column("completed_at", sa.DateTime(timezone=True)),
        sa.Column("latency_ms", sa.Integer()),
        sa.Column("attempts", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("finish_reason", sa.String(100)),
        sa.Column("input_tokens", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("output_tokens", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("total_tokens", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("estimated_cost_usd", sa.Float(), nullable=False, server_default="0"),
        sa.Column("fallback_chain", sa.JSON(), nullable=False, server_default="[]"),
        sa.Column("error_code", sa.String(100)),
        sa.Column("encrypted_debug_payload", sa.Text()),
        sa.Column("debug_expires_at", sa.DateTime(timezone=True)),
    )
    op.create_index("ix_ai_runs_user_created", "ai_runs", ["user_id", "started_at"])
    op.create_index(
        "ix_ai_runs_item_version", "ai_runs", ["item_id", "analysis_version"]
    )
    op.create_index("ix_ai_runs_provider_status", "ai_runs", ["provider", "status"])
    op.create_table(
        "ai_field_provenance",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column(
            "run_id",
            sa.String(36),
            sa.ForeignKey("ai_runs.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "user_id",
            sa.String(36),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
        ),
        sa.Column(
            "item_id",
            sa.String(36),
            sa.ForeignKey("items.id", ondelete="CASCADE"),
        ),
        sa.Column("analysis_version", sa.Integer()),
        sa.Column("field_name", sa.String(60), nullable=False),
        sa.Column("source", sa.String(30), nullable=False),
        sa.Column("provider", sa.String(40), nullable=False),
        sa.Column("model", sa.String(255)),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
    )
    op.create_index(
        "ix_ai_field_item_version",
        "ai_field_provenance",
        ["item_id", "analysis_version"],
    )
    op.create_table(
        "item_embeddings",
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
        sa.Column("analysis_version", sa.Integer(), nullable=False),
        sa.Column("chunk_id", sa.String(64), nullable=False),
        sa.Column("model", sa.String(255), nullable=False),
        sa.Column("dimensions", sa.Integer(), nullable=False),
        sa.Column("vector", sa.JSON(), nullable=False),
        sa.Column("content_hash", sa.String(64), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.UniqueConstraint(
            "item_id",
            "analysis_version",
            "chunk_id",
            "model",
            name="uq_item_embedding",
        ),
    )
    op.create_index("ix_item_embeddings_user", "item_embeddings", ["user_id"])


def downgrade() -> None:
    op.drop_index("ix_item_embeddings_user", table_name="item_embeddings")
    op.drop_table("item_embeddings")
    op.drop_index("ix_ai_field_item_version", table_name="ai_field_provenance")
    op.drop_table("ai_field_provenance")
    op.drop_index("ix_ai_runs_provider_status", table_name="ai_runs")
    op.drop_index("ix_ai_runs_item_version", table_name="ai_runs")
    op.drop_index("ix_ai_runs_user_created", table_name="ai_runs")
    op.drop_table("ai_runs")
