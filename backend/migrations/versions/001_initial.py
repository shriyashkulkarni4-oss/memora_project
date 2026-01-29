"""Initial migration - Create all tables

Revision ID: 001
Revises:
Create Date: 2024-01-01 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = '001'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create users table
    op.create_table(
        'users',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('email', sa.String(255), unique=True, nullable=False, index=True),
        sa.Column('hashed_password', sa.String(255), nullable=False),
        sa.Column('name', sa.String(255), nullable=True),
        sa.Column('is_active', sa.Boolean(), default=True, nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.func.now(), onupdate=sa.func.now()),
    )

    # Create categories table
    op.create_table(
        'categories',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('user_id', sa.String(36), sa.ForeignKey('users.id'), nullable=False),
        sa.Column('name', sa.String(100), nullable=False),
        sa.Column('color', sa.String(20), default='#3b82f6', nullable=False),
        sa.Column('icon', sa.String(50), default='FolderOpen', nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.func.now(), onupdate=sa.func.now()),
    )

    # Create tags table
    op.create_table(
        'tags',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('name', sa.String(50), unique=True, nullable=False, index=True),
        sa.Column('color', sa.String(20), default='#6b7280', nullable=False),
    )

    # Create links table
    op.create_table(
        'links',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('user_id', sa.String(36), sa.ForeignKey('users.id'), nullable=False),
        sa.Column('url', sa.Text(), nullable=True),
        sa.Column('title', sa.String(500), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('favicon', sa.Text(), nullable=True),
        sa.Column('source', sa.String(20), default='manual', nullable=False),
        sa.Column('status', sa.String(20), default='pending', nullable=False),
        sa.Column('category_id', sa.String(36), sa.ForeignKey('categories.id'), nullable=True),
        sa.Column('ai_summary', sa.JSON(), nullable=True),
        sa.Column('screenshot_data', sa.JSON(), nullable=True),
        sa.Column('is_favorite', sa.Boolean(), default=False, nullable=False),
        sa.Column('is_archived', sa.Boolean(), default=False, nullable=False),
        sa.Column('read_count', sa.Integer(), default=0, nullable=False),
        sa.Column('last_visited_at', sa.DateTime(), nullable=True),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.func.now(), onupdate=sa.func.now()),
    )

    # Create link_tags association table
    op.create_table(
        'link_tags',
        sa.Column('link_id', sa.String(36), sa.ForeignKey('links.id', ondelete='CASCADE'), primary_key=True),
        sa.Column('tag_id', sa.String(36), sa.ForeignKey('tags.id', ondelete='CASCADE'), primary_key=True),
    )

    # Create indexes
    op.create_index('ix_links_user_id', 'links', ['user_id'])
    op.create_index('ix_links_category_id', 'links', ['category_id'])
    op.create_index('ix_links_created_at', 'links', ['created_at'])
    op.create_index('ix_categories_user_id', 'categories', ['user_id'])


def downgrade() -> None:
    op.drop_table('link_tags')
    op.drop_table('links')
    op.drop_table('tags')
    op.drop_table('categories')
    op.drop_table('users')
