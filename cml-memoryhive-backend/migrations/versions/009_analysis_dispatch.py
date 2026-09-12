"""Make processing jobs the transactional analysis dispatch outbox.

Revision ID: 009
Revises: 008
Create Date: 2026-09-12 00:00:00
"""

from collections.abc import Sequence
from datetime import datetime, timezone
import uuid

import sqlalchemy as sa
from alembic import op

revision: str = "009"
down_revision: str | None = "008"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "processing_jobs", sa.Column("analysis_version", sa.Integer(), nullable=True)
    )
    op.add_column(
        "processing_jobs",
        sa.Column(
            "execution_backend",
            sa.String(20),
            nullable=False,
            server_default="database",
        ),
    )
    op.add_column(
        "processing_jobs",
        sa.Column("reason", sa.String(40), nullable=False, server_default="capture"),
    )
    op.add_column(
        "processing_jobs",
        sa.Column("temporal_workflow_id", sa.String(255), nullable=True),
    )
    with op.batch_alter_table("processing_jobs") as batch_op:
        batch_op.create_unique_constraint(
            "uq_processing_jobs_item_analysis_version",
            ["item_id", "analysis_version"],
        )
    op.create_index(
        "ix_processing_jobs_backend_claim",
        "processing_jobs",
        ["execution_backend", "status", "next_attempt_at", "created_at"],
    )

    # Repair scheduling intent for items that were left pending without an
    # executable legacy job. Existing processing jobs keep a NULL version so
    # historical retries cannot conflict with the new per-version invariant.
    connection = op.get_bind()
    pending_items = connection.execute(sa.text("""
            SELECT i.id, i.type, i.analysis_version, i.analysis_requested_at
            FROM items AS i
            WHERE i.deleted_at IS NULL
              AND i.analysis_status = 'pending'
              AND NOT EXISTS (
                SELECT 1
                FROM processing_jobs AS p
                WHERE p.item_id = i.id
                  AND p.status IN ('pending', 'processing', 'scheduled')
              )
            """)).mappings()
    now = datetime.now(timezone.utc)
    for item in pending_items:
        connection.execute(
            sa.text("""
                INSERT INTO processing_jobs (
                    id, item_id, kind, analysis_version, execution_backend,
                    reason, status, attempts, max_attempts, next_attempt_at,
                    created_at, updated_at
                ) VALUES (
                    :id, :item_id, :kind, :analysis_version, 'database',
                    'migration_repair', 'pending', 0, 3, :now, :now, :now
                )
                """),
            {
                "id": str(uuid.uuid4()),
                "item_id": item["id"],
                "kind": item["type"],
                "analysis_version": item["analysis_version"],
                "now": item["analysis_requested_at"] or now,
            },
        )


def downgrade() -> None:
    op.drop_index("ix_processing_jobs_backend_claim", table_name="processing_jobs")
    with op.batch_alter_table("processing_jobs") as batch_op:
        batch_op.drop_constraint(
            "uq_processing_jobs_item_analysis_version", type_="unique"
        )
    op.drop_column("processing_jobs", "temporal_workflow_id")
    op.drop_column("processing_jobs", "reason")
    op.drop_column("processing_jobs", "execution_backend")
    op.drop_column("processing_jobs", "analysis_version")
