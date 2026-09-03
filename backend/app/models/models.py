"""
SQLAlchemy Models for Memoryhive
"""

import enum
from datetime import datetime
from typing import List, Optional

from sqlalchemy import (
    JSON,
    Boolean,
    Column,
    DateTime,
    Enum,
    ForeignKey,
    Integer,
    String,
    Table,
    Text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class LinkSource(str, enum.Enum):
    TWITTER = "twitter"
    LINKEDIN = "linkedin"
    YOUTUBE = "youtube"
    GITHUB = "github"
    ARTICLE = "article"
    NEWS = "news"
    SCREENSHOT = "screenshot"
    MANUAL = "manual"
    OTHER = "other"


class LinkStatus(str, enum.Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    PROCESSED = "processed"
    FAILED = "failed"


# Association table for many-to-many relationship between links and tags
link_tags = Table(
    "link_tags",
    Base.metadata,
    Column("link_id", String, ForeignKey("links.id"), primary_key=True),
    Column("tag_id", String, ForeignKey("tags.id"), primary_key=True),
)


class User(Base):
    __tablename__ = "users"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    hashed_password: Mapped[str] = mapped_column(String(255))
    name: Mapped[Optional[str]] = mapped_column(String(255))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    # Relationships
    links: Mapped[List["Link"]] = relationship(
        "Link", back_populates="user", cascade="all, delete-orphan"
    )
    categories: Mapped[List["Category"]] = relationship(
        "Category", back_populates="user", cascade="all, delete-orphan"
    )


class Category(Base):
    __tablename__ = "categories"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id"))
    name: Mapped[str] = mapped_column(String(100))
    color: Mapped[str] = mapped_column(String(20), default="#3b82f6")
    icon: Mapped[str] = mapped_column(String(50), default="FolderOpen")
    description: Mapped[Optional[str]] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    # Relationships
    user: Mapped["User"] = relationship("User", back_populates="categories")
    links: Mapped[List["Link"]] = relationship("Link", back_populates="category")


class Tag(Base):
    __tablename__ = "tags"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    name: Mapped[str] = mapped_column(String(50), unique=True, index=True)
    color: Mapped[str] = mapped_column(String(20), default="#6b7280")

    # Relationships
    links: Mapped[List["Link"]] = relationship(
        "Link", secondary=link_tags, back_populates="tags"
    )


class Link(Base):
    __tablename__ = "links"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id"))
    url: Mapped[Optional[str]] = mapped_column(Text)
    title: Mapped[str] = mapped_column(String(500))
    description: Mapped[Optional[str]] = mapped_column(Text)
    favicon: Mapped[Optional[str]] = mapped_column(Text)

    source: Mapped[LinkSource] = mapped_column(
        Enum(LinkSource), default=LinkSource.MANUAL
    )
    status: Mapped[LinkStatus] = mapped_column(
        Enum(LinkStatus), default=LinkStatus.PENDING
    )

    category_id: Mapped[Optional[str]] = mapped_column(
        String(36), ForeignKey("categories.id")
    )

    # AI Summary stored as JSON
    ai_summary: Mapped[Optional[dict]] = mapped_column(JSON)

    # Screenshot data stored as JSON
    screenshot_data: Mapped[Optional[dict]] = mapped_column(JSON)

    is_favorite: Mapped[bool] = mapped_column(Boolean, default=False)
    is_archived: Mapped[bool] = mapped_column(Boolean, default=False)
    read_count: Mapped[int] = mapped_column(Integer, default=0)
    last_visited_at: Mapped[Optional[datetime]] = mapped_column(DateTime)
    notes: Mapped[Optional[str]] = mapped_column(Text)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    # Relationships
    user: Mapped["User"] = relationship("User", back_populates="links")
    category: Mapped[Optional["Category"]] = relationship(
        "Category", back_populates="links"
    )
    tags: Mapped[List["Tag"]] = relationship(
        "Tag", secondary=link_tags, back_populates="links"
    )
