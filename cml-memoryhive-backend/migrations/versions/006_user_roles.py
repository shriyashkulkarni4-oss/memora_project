"""Add user personas for admin access.

Revision ID: 006
Revises: 005
Create Date: 2026-09-06 00:00:00
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "006"
down_revision: str | None = "005"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "users",
        sa.Column("role", sa.String(20), nullable=False, server_default="user"),
    )
    op.execute(
        sa.text(
            """
            UPDATE users
            SET role = 'admin'
            WHERE id = (
                SELECT id FROM users ORDER BY created_at ASC, email ASC LIMIT 1
            )
            """
        )
    )


def downgrade() -> None:
    op.drop_column("users", "role")
