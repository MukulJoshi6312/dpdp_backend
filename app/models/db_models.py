"""ORM models for the Nyaykosh backend.

Laws and personas keep their rich nested shape (provisions/penalties,
triggers/rules) in JSONB columns. Frequently-queried scalar fields are
mirrored into real columns so they can be filtered/indexed in SQL.
"""
from __future__ import annotations

from typing import Any, Dict, List

from sqlalchemy import Boolean, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class LawModel(Base):
    __tablename__ = "laws"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    api_slug: Mapped[str] = mapped_column(String, index=True, unique=True)
    title: Mapped[str] = mapped_column(String, index=True)
    year: Mapped[int] = mapped_column(Integer)
    category: Mapped[str] = mapped_column(String, index=True)
    status: Mapped[str] = mapped_column(String, index=True)
    short_desc: Mapped[str] = mapped_column(Text, default="")
    # Full law record (matches schemas.law.Law), the source of truth for reads.
    data: Mapped[Dict[str, Any]] = mapped_column(JSONB)


class PersonaModel(Base):
    __tablename__ = "personas"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    label: Mapped[str] = mapped_column(String)
    # Ordering so personas come back in a stable, insertion-like order.
    position: Mapped[int] = mapped_column(Integer, default=0, index=True)
    # Full persona record (matches schemas.simulator.Persona).
    data: Mapped[Dict[str, Any]] = mapped_column(JSONB)


class SiteContentModel(Base):
    """Singleton-ish key/value store for static content (site, navigation)."""

    __tablename__ = "site_content"

    key: Mapped[str] = mapped_column(String, primary_key=True)
    data: Mapped[Any] = mapped_column(JSONB)


class AdminUserModel(Base):
    __tablename__ = "admin_users"

    email: Mapped[str] = mapped_column(String, primary_key=True)
    password_hash: Mapped[str] = mapped_column(String)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
