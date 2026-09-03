"""Replace prototype links with the canonical user-owned Item model.

Revision ID: 002
Revises: 001
Create Date: 2026-09-03 00:00:00
"""

import json
import uuid
from collections.abc import Sequence
from typing import Any

import sqlalchemy as sa
from alembic import op

revision: str = "002"
down_revision: str | None = "001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _json_value(value: Any) -> dict[str, Any] | None:
    if isinstance(value, dict):
        return value
    if isinstance(value, str):
        try:
            decoded = json.loads(value)
            return decoded if isinstance(decoded, dict) else None
        except json.JSONDecodeError:
            return None
    return None


def _create_canonical_tables() -> None:
    op.create_table(
        "tags",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column(
            "user_id",
            sa.String(36),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("name", sa.String(50), nullable=False),
        sa.Column("color", sa.String(20), nullable=False, server_default="#6b7280"),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.UniqueConstraint("user_id", "name", name="uq_tags_user_name"),
    )
    op.create_index("ix_tags_user_id", "tags", ["user_id"])

    op.create_table(
        "items",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column(
            "user_id",
            sa.String(36),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("type", sa.String(20), nullable=False),
        sa.Column("url", sa.Text()),
        sa.Column("raw_text", sa.Text()),
        sa.Column("title", sa.String(500)),
        sa.Column("description", sa.Text()),
        sa.Column("notes", sa.Text()),
        sa.Column("source", sa.String(100)),
        sa.Column("source_domain", sa.String(255)),
        sa.Column("author", sa.String(255)),
        sa.Column("published_at", sa.DateTime(timezone=True)),
        sa.Column("favicon_url", sa.Text()),
        sa.Column("extracted_text", sa.Text()),
        sa.Column("normalized_text", sa.Text()),
        sa.Column("language", sa.String(20)),
        sa.Column("summary", sa.Text()),
        sa.Column("metadata", sa.JSON()),
        sa.Column(
            "processing_status", sa.String(20), nullable=False, server_default="pending"
        ),
        sa.Column("processing_error", sa.Text()),
        sa.Column(
            "category_id",
            sa.String(36),
            sa.ForeignKey("categories.id", ondelete="SET NULL"),
        ),
        sa.Column(
            "is_favorite", sa.Boolean(), nullable=False, server_default=sa.false()
        ),
        sa.Column(
            "is_archived", sa.Boolean(), nullable=False, server_default=sa.false()
        ),
        sa.Column("read_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("last_visited_at", sa.DateTime(timezone=True)),
        sa.Column("revision", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("deleted_at", sa.DateTime(timezone=True)),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.CheckConstraint(
            "(type != 'link' OR url IS NOT NULL) AND "
            "(type != 'text' OR raw_text IS NOT NULL)",
            name="ck_items_required_content",
        ),
        sa.CheckConstraint("revision > 0", name="ck_items_revision_positive"),
    )
    op.create_index("ix_items_user_created", "items", ["user_id", "created_at"])
    op.create_index("ix_items_user_updated", "items", ["user_id", "updated_at"])
    op.create_index("ix_items_user_type", "items", ["user_id", "type"])
    op.create_index("ix_items_category_id", "items", ["category_id"])
    op.create_index("ix_items_deleted_at", "items", ["deleted_at"])

    op.create_table(
        "assets",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column(
            "item_id",
            sa.String(36),
            sa.ForeignKey("items.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "user_id",
            sa.String(36),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("object_key", sa.Text(), nullable=False),
        sa.Column("original_filename", sa.String(255)),
        sa.Column("mime_type", sa.String(100), nullable=False),
        sa.Column("size_bytes", sa.Integer(), nullable=False),
        sa.Column("sha256", sa.String(64)),
        sa.Column("width", sa.Integer()),
        sa.Column("height", sa.Integer()),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.CheckConstraint("size_bytes >= 0", name="ck_assets_size_nonnegative"),
        sa.UniqueConstraint("object_key", name="uq_assets_object_key"),
    )
    op.create_index("ix_assets_item_id", "assets", ["item_id"])
    op.create_index("ix_assets_user_id", "assets", ["user_id"])

    op.create_table(
        "item_tags",
        sa.Column(
            "item_id",
            sa.String(36),
            sa.ForeignKey("items.id", ondelete="CASCADE"),
            primary_key=True,
        ),
        sa.Column(
            "tag_id",
            sa.String(36),
            sa.ForeignKey("tags.id", ondelete="CASCADE"),
            primary_key=True,
        ),
    )


def _migrate_legacy_data() -> None:
    bind = op.get_bind()
    links = list(bind.execute(sa.text("SELECT * FROM legacy_links")).mappings())
    now = sa.func.now()

    for link in links:
        source = str(link["source"] or "manual").lower()
        old_status = str(link["status"] or "pending").lower()
        status_map = {
            "processed": "ready",
            "pending": "pending",
            "processing": "processing",
            "failed": "failed",
        }
        screenshot = _json_value(link["screenshot_data"])
        item_type = "screenshot" if source == "screenshot" or screenshot else "link"
        bind.execute(
            sa.text(
                """
                INSERT INTO items (
                    id, user_id, type, url, title, description, notes, source,
                    favicon_url, summary, metadata, processing_status, category_id,
                    is_favorite, is_archived, read_count, last_visited_at, revision,
                    created_at, updated_at
                ) VALUES (
                    :id, :user_id, :type, :url, :title, :description, :notes, :source,
                    :favicon_url, :summary, :metadata, :processing_status, :category_id,
                    :is_favorite, :is_archived, :read_count, :last_visited_at, 1,
                    :created_at, :updated_at
                )
                """
            ).bindparams(sa.bindparam("metadata", type_=sa.JSON())),
            {
                "id": link["id"],
                "user_id": link["user_id"],
                "type": item_type,
                "url": link["url"],
                "title": link["title"],
                "description": link["description"],
                "notes": link["notes"],
                "source": source,
                "favicon_url": link["favicon"],
                "summary": (_json_value(link["ai_summary"]) or {}).get("summary"),
                "metadata": screenshot,
                "processing_status": status_map.get(old_status, "pending"),
                "category_id": link["category_id"],
                "is_favorite": link["is_favorite"],
                "is_archived": link["is_archived"],
                "read_count": link["read_count"],
                "last_visited_at": link["last_visited_at"],
                "created_at": link["created_at"] or now,
                "updated_at": link["updated_at"] or now,
            },
        )
        if screenshot and screenshot.get("file_key"):
            asset_id = str(
                uuid.uuid5(
                    uuid.NAMESPACE_URL,
                    f"memoryhive:{link['id']}:{screenshot['file_key']}",
                )
            )
            bind.execute(
                sa.text(
                    """
                    INSERT INTO assets (
                        id, item_id, user_id, object_key, mime_type, size_bytes, created_at
                    ) VALUES (
                        :id, :item_id, :user_id, :object_key, :mime_type, :size_bytes,
                        :created_at
                    )
                    """
                ),
                {
                    "id": asset_id,
                    "item_id": link["id"],
                    "user_id": link["user_id"],
                    "object_key": screenshot["file_key"],
                    "mime_type": screenshot.get("content_type") or "image/png",
                    "size_bytes": int(screenshot.get("file_size") or 0),
                    "created_at": link["created_at"],
                },
            )

    associations = bind.execute(
        sa.text(
            """
            SELECT DISTINCT lt.link_id, l.user_id, t.id AS old_tag_id, t.name, t.color
            FROM legacy_link_tags lt
            JOIN legacy_links l ON l.id = lt.link_id
            JOIN legacy_tags t ON t.id = lt.tag_id
            """
        )
    ).mappings()
    inserted_tags: set[str] = set()
    for association in associations:
        tag_id = str(
            uuid.uuid5(
                uuid.NAMESPACE_URL,
                f"memoryhive:{association['user_id']}:{association['old_tag_id']}",
            )
        )
        if tag_id not in inserted_tags:
            bind.execute(
                sa.text(
                    """
                    INSERT INTO tags (id, user_id, name, color, created_at, updated_at)
                    VALUES (:id, :user_id, :name, :color, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
                    """
                ),
                {
                    "id": tag_id,
                    "user_id": association["user_id"],
                    "name": str(association["name"]).lower(),
                    "color": association["color"] or "#6b7280",
                },
            )
            inserted_tags.add(tag_id)
        bind.execute(
            sa.text(
                "INSERT INTO item_tags (item_id, tag_id) VALUES (:item_id, :tag_id)"
            ),
            {"item_id": association["link_id"], "tag_id": tag_id},
        )


def upgrade() -> None:
    op.rename_table("links", "legacy_links")
    op.rename_table("tags", "legacy_tags")
    op.rename_table("link_tags", "legacy_link_tags")
    _create_canonical_tables()
    _migrate_legacy_data()
    op.drop_table("legacy_link_tags")
    op.drop_table("legacy_links")
    op.drop_table("legacy_tags")
    op.create_index(
        "uq_categories_user_name", "categories", ["user_id", "name"], unique=True
    )


def downgrade() -> None:
    op.drop_index("uq_categories_user_name", table_name="categories")
    op.create_table(
        "links",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("user_id", sa.String(36), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("url", sa.Text()),
        sa.Column("title", sa.String(500), nullable=False),
        sa.Column("description", sa.Text()),
        sa.Column("favicon", sa.Text()),
        sa.Column("source", sa.String(20), nullable=False, server_default="manual"),
        sa.Column("status", sa.String(20), nullable=False, server_default="pending"),
        sa.Column("category_id", sa.String(36), sa.ForeignKey("categories.id")),
        sa.Column("ai_summary", sa.JSON()),
        sa.Column("screenshot_data", sa.JSON()),
        sa.Column(
            "is_favorite", sa.Boolean(), nullable=False, server_default=sa.false()
        ),
        sa.Column(
            "is_archived", sa.Boolean(), nullable=False, server_default=sa.false()
        ),
        sa.Column("read_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("last_visited_at", sa.DateTime()),
        sa.Column("notes", sa.Text()),
        sa.Column(
            "created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()
        ),
        sa.Column(
            "updated_at", sa.DateTime(), nullable=False, server_default=sa.func.now()
        ),
    )
    op.create_index("ix_links_user_id", "links", ["user_id"])
    op.create_index("ix_links_category_id", "links", ["category_id"])
    op.create_index("ix_links_created_at", "links", ["created_at"])
    op.create_table(
        "tags_legacy_out",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("name", sa.String(50), nullable=False),
        sa.Column("color", sa.String(20), nullable=False, server_default="#6b7280"),
    )
    op.create_table(
        "link_tags_legacy_out",
        sa.Column("link_id", sa.String(36), primary_key=True),
        sa.Column("tag_id", sa.String(36), primary_key=True),
    )

    bind = op.get_bind()
    items = bind.execute(sa.text("SELECT * FROM items")).mappings()
    for item in items:
        asset = (
            bind.execute(
                sa.text("SELECT * FROM assets WHERE item_id = :item_id LIMIT 1"),
                {"item_id": item["id"]},
            )
            .mappings()
            .first()
        )
        screenshot_data = None
        if asset:
            screenshot_data = {
                "file_key": asset["object_key"],
                "file_size": asset["size_bytes"],
                "content_type": asset["mime_type"],
            }
        title = item["title"] or item["url"] or "Saved item"
        bind.execute(
            sa.text(
                """
                INSERT INTO links (
                    id, user_id, url, title, description, favicon, source, status,
                    category_id, ai_summary, screenshot_data, is_favorite, is_archived,
                    read_count, last_visited_at, notes, created_at, updated_at
                ) VALUES (
                    :id, :user_id, :url, :title, :description, :favicon, :source, :status,
                    :category_id, :ai_summary, :screenshot_data, :is_favorite, :is_archived,
                    :read_count, :last_visited_at, :notes, :created_at, :updated_at
                )
                """
            ).bindparams(
                sa.bindparam("ai_summary", type_=sa.JSON()),
                sa.bindparam("screenshot_data", type_=sa.JSON()),
            ),
            {
                "id": item["id"],
                "user_id": item["user_id"],
                "url": item["url"],
                "title": title,
                "description": item["description"],
                "favicon": item["favicon_url"],
                "source": (
                    "screenshot"
                    if item["type"] == "screenshot"
                    else (item["source"] or "manual")
                ),
                "status": (
                    "processed"
                    if item["processing_status"] == "ready"
                    else item["processing_status"]
                ),
                "category_id": item["category_id"],
                "ai_summary": {"summary": item["summary"]} if item["summary"] else None,
                "screenshot_data": screenshot_data,
                "is_favorite": item["is_favorite"],
                "is_archived": item["is_archived"],
                "read_count": item["read_count"],
                "last_visited_at": item["last_visited_at"],
                "notes": item["notes"],
                "created_at": item["created_at"],
                "updated_at": item["updated_at"],
            },
        )

    old_tag_by_name: dict[str, str] = {}
    for tag in bind.execute(sa.text("SELECT * FROM tags ORDER BY id")).mappings():
        old_id = old_tag_by_name.get(tag["name"])
        if old_id is None:
            old_id = tag["id"]
            old_tag_by_name[tag["name"]] = old_id
            bind.execute(
                sa.text(
                    "INSERT INTO tags_legacy_out (id, name, color) VALUES (:id, :name, :color)"
                ),
                {"id": old_id, "name": tag["name"], "color": tag["color"]},
            )
        item_ids = bind.execute(
            sa.text("SELECT item_id FROM item_tags WHERE tag_id = :tag_id"),
            {"tag_id": tag["id"]},
        ).scalars()
        for item_id in item_ids:
            bind.execute(
                sa.text(
                    "INSERT INTO link_tags_legacy_out (link_id, tag_id) VALUES (:item_id, :tag_id)"
                ),
                {"item_id": item_id, "tag_id": old_id},
            )

    op.drop_table("item_tags")
    op.drop_table("assets")
    op.drop_table("items")
    op.drop_table("tags")
    op.rename_table("tags_legacy_out", "tags")
    op.rename_table("link_tags_legacy_out", "link_tags")
    op.create_index("ix_tags_name", "tags", ["name"], unique=True)
