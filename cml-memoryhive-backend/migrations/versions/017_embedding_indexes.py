"""Add versioned chunks and embedding index identity.

Revision ID: 017
Revises: 016
Create Date: 2026-09-12 00:00:00
"""

from collections.abc import Sequence
from uuid import uuid4

import sqlalchemy as sa
from alembic import op

revision: str = "017"
down_revision: str | None = "016"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "embedding_indexes",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("provider", sa.String(40), nullable=False),
        sa.Column("model", sa.String(255), nullable=False),
        sa.Column("dimensions", sa.Integer(), nullable=False),
        sa.Column("normalization", sa.String(20), nullable=False, server_default="l2"),
        sa.Column("version", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("status", sa.String(20), nullable=False, server_default="active"),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.UniqueConstraint(
            "provider",
            "model",
            "dimensions",
            "normalization",
            "version",
            name="uq_embedding_index_schema",
        ),
    )
    op.create_table(
        "document_chunks",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("chunk_key", sa.String(100), nullable=False),
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
        sa.Column("ordinal", sa.Integer(), nullable=False),
        sa.Column("text", sa.Text(), nullable=False),
        sa.Column("start_offset", sa.Integer(), nullable=False),
        sa.Column("end_offset", sa.Integer(), nullable=False),
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
            "ordinal",
            name="uq_document_chunk_ordinal",
        ),
    )
    op.create_index(
        "ix_document_chunk_hash", "document_chunks", ["user_id", "content_hash"]
    )
    with op.batch_alter_table("item_embeddings") as batch:
        batch.drop_constraint("uq_item_embedding", type_="unique")
        batch.add_column(sa.Column("index_id", sa.String(36)))
        batch.add_column(
            sa.Column(
                "provider", sa.String(40), nullable=False, server_default="legacy"
            )
        )
        batch.add_column(
            sa.Column(
                "normalization", sa.String(20), nullable=False, server_default="l2"
            )
        )
        batch.add_column(
            sa.Column("index_version", sa.Integer(), nullable=False, server_default="1")
        )
        batch.create_foreign_key(
            "fk_item_embedding_index",
            "embedding_indexes",
            ["index_id"],
            ["id"],
            ondelete="RESTRICT",
        )

    connection = op.get_bind()
    schemas = connection.execute(
        sa.text("SELECT DISTINCT model, dimensions FROM item_embeddings")
    ).all()
    for model, dimensions in schemas:
        index_id = str(uuid4())
        connection.execute(
            sa.text(
                "INSERT INTO embedding_indexes "
                "(id, provider, model, dimensions, normalization, version, status) "
                "VALUES (:id, 'legacy', :model, :dimensions, 'l2', 1, 'legacy')"
            ),
            {"id": index_id, "model": model, "dimensions": dimensions},
        )
        connection.execute(
            sa.text(
                "UPDATE item_embeddings SET index_id = :id "
                "WHERE model = :model AND dimensions = :dimensions"
            ),
            {"id": index_id, "model": model, "dimensions": dimensions},
        )

    with op.batch_alter_table("item_embeddings") as batch:
        batch.alter_column("index_id", existing_type=sa.String(36), nullable=False)
        batch.create_unique_constraint(
            "uq_item_embedding",
            ["item_id", "analysis_version", "chunk_id", "index_id"],
        )
    op.create_index(
        "ix_item_embeddings_index_hash",
        "item_embeddings",
        ["index_id", "content_hash"],
    )


def downgrade() -> None:
    op.drop_index("ix_item_embeddings_index_hash", table_name="item_embeddings")
    with op.batch_alter_table("item_embeddings") as batch:
        batch.drop_constraint("uq_item_embedding", type_="unique")
        batch.drop_constraint("fk_item_embedding_index", type_="foreignkey")
        batch.drop_column("index_version")
        batch.drop_column("normalization")
        batch.drop_column("provider")
        batch.drop_column("index_id")
        batch.create_unique_constraint(
            "uq_item_embedding",
            ["item_id", "analysis_version", "chunk_id", "model"],
        )
    op.drop_index("ix_document_chunk_hash", table_name="document_chunks")
    op.drop_table("document_chunks")
    op.drop_table("embedding_indexes")
