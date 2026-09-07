"""Add URL deduplication, search indexes, and lifecycle cleanup records.

Revision ID: 004
Revises: 003
Create Date: 2026-09-04 00:00:00
"""

from collections.abc import Sequence
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

import sqlalchemy as sa
from alembic import op

revision: str = "004"
down_revision: str | None = "003"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _normalize(value: str) -> str:
    parsed = urlsplit(value.strip())
    hostname = (parsed.hostname or "").lower().rstrip(".")
    port = parsed.port
    if port and not (
        (parsed.scheme.lower() == "http" and port == 80)
        or (parsed.scheme.lower() == "https" and port == 443)
    ):
        hostname = f"{hostname}:{port}"
    path = (parsed.path or "/").rstrip("/") or "/"
    ignored = {"fbclid", "gclid", "mc_cid", "mc_eid", "ref_src"}
    query = urlencode(
        sorted(
            (key, value)
            for key, value in parse_qsl(parsed.query, keep_blank_values=True)
            if not key.lower().startswith("utm_") and key.lower() not in ignored
        )
    )
    return urlunsplit((parsed.scheme.lower(), hostname, path, query, ""))


def upgrade() -> None:
    op.add_column("items", sa.Column("normalized_url", sa.Text(), nullable=True))
    bind = op.get_bind()
    seen: set[tuple[str, str]] = set()
    rows = bind.execute(
        sa.text(
            "SELECT id, user_id, url FROM items WHERE url IS NOT NULL ORDER BY created_at, id"
        )
    ).mappings()
    for row in rows:
        normalized = _normalize(row["url"])
        key = (row["user_id"], normalized)
        if key in seen:
            continue
        seen.add(key)
        bind.execute(
            sa.text("UPDATE items SET normalized_url = :url WHERE id = :id"),
            {"url": normalized, "id": row["id"]},
        )

    active = sa.text("normalized_url IS NOT NULL AND deleted_at IS NULL")
    op.create_index(
        "uq_items_user_normalized_url_active",
        "items",
        ["user_id", "normalized_url"],
        unique=True,
        postgresql_where=active,
        sqlite_where=active,
    )
    if bind.dialect.name == "postgresql":
        op.execute(
            sa.text(
                """
            CREATE INDEX ix_items_search_document ON items USING GIN (
              to_tsvector('simple'::regconfig,
                coalesce(title, '') || ' ' || coalesce(url, '') || ' ' ||
                coalesce(raw_text, '') || ' ' || coalesce(extracted_text, '') || ' ' ||
                coalesce(summary, '') || ' ' || coalesce(description, '') || ' ' ||
                coalesce(notes, '') || ' ' || coalesce(source_domain, ''))
            )
        """
            )
        )

    op.create_table(
        "lifecycle_audits",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("user_id", sa.String(36), nullable=False),
        sa.Column("event", sa.String(50), nullable=False),
        sa.Column("status", sa.String(20), nullable=False, server_default="pending"),
        sa.Column("object_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("error_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column("completed_at", sa.DateTime(timezone=True)),
    )
    op.create_index("ix_lifecycle_audits_user_id", "lifecycle_audits", ["user_id"])
    op.create_table(
        "storage_deletion_jobs",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column(
            "audit_id",
            sa.String(36),
            sa.ForeignKey("lifecycle_audits.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("object_key", sa.Text(), nullable=False),
        sa.Column("attempts", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("last_error", sa.Text()),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
    )
    op.create_index(
        "ix_storage_deletion_jobs_audit_id", "storage_deletion_jobs", ["audit_id"]
    )


def downgrade() -> None:
    op.drop_index(
        "ix_storage_deletion_jobs_audit_id", table_name="storage_deletion_jobs"
    )
    op.drop_table("storage_deletion_jobs")
    op.drop_index("ix_lifecycle_audits_user_id", table_name="lifecycle_audits")
    op.drop_table("lifecycle_audits")
    if op.get_bind().dialect.name == "postgresql":
        op.drop_index("ix_items_search_document", table_name="items")
    op.drop_index("uq_items_user_normalized_url_active", table_name="items")
    op.drop_column("items", "normalized_url")
