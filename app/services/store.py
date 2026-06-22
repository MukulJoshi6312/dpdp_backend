"""Data-access layer backed by PostgreSQL (SQLAlchemy 2.0).

Routers depend only on these functions; the storage backend (DB) is hidden here.
Laws and personas are stored as JSONB so the nested shapes survive round-trips
unchanged. Each function takes an active Session.
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.db_models import (
    AdminUserModel,
    LawModel,
    PersonaModel,
    SiteContentModel,
)


# --- Laws -----------------------------------------------------------------

def read_laws(db: Session) -> List[Dict[str, Any]]:
    rows = db.execute(select(LawModel).order_by(LawModel.year.desc(), LawModel.id)).scalars().all()
    return [r.data for r in rows]


def get_law_id_set(db: Session) -> set:
    return set(db.execute(select(LawModel.id)).scalars().all())


def find_law(db: Session, slug: str) -> Optional[Dict[str, Any]]:
    row = db.execute(
        select(LawModel).where((LawModel.api_slug == slug) | (LawModel.id == slug))
    ).scalars().first()
    return row.data if row else None


def insert_law(db: Session, law: Dict[str, Any]) -> None:
    db.add(_law_row(law))
    db.commit()


def update_law(db: Session, law_id: str, law: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    row = db.get(LawModel, law_id)
    if row is None:
        return None
    _apply_law(row, law)
    db.commit()
    return row.data


def delete_law(db: Session, law_id: str) -> bool:
    row = db.get(LawModel, law_id)
    if row is None:
        return False
    db.delete(row)
    db.commit()
    return True


# --- Law PDF (uploaded official copy) -------------------------------------

def _find_law_row(db: Session, slug: str) -> Optional[LawModel]:
    """Resolve a law row by id or apiSlug (mirrors find_law)."""
    return db.execute(
        select(LawModel).where((LawModel.api_slug == slug) | (LawModel.id == slug))
    ).scalars().first()


def set_law_pdf(db: Session, slug: str, content: bytes, filename: str) -> bool:
    row = _find_law_row(db, slug)
    if row is None:
        return False
    row.pdf_bytes = content
    row.pdf_filename = filename
    db.commit()
    return True


def get_law_pdf(db: Session, slug: str) -> Optional[tuple]:
    """Return (bytes, filename) for the uploaded PDF, or None if not set."""
    row = _find_law_row(db, slug)
    if row is None or row.pdf_bytes is None:
        return None
    return row.pdf_bytes, row.pdf_filename or f"{row.id}.pdf"


def delete_law_pdf(db: Session, slug: str) -> bool:
    row = _find_law_row(db, slug)
    if row is None or row.pdf_bytes is None:
        return False
    row.pdf_bytes = None
    row.pdf_filename = None
    db.commit()
    return True


def law_has_pdf(db: Session, slug: str) -> bool:
    row = _find_law_row(db, slug)
    return row is not None and row.pdf_bytes is not None


def law_ids_with_pdf(db: Session) -> set:
    """Set of law ids that have an uploaded PDF (single query, for list views)."""
    return set(
        db.execute(
            select(LawModel.id).where(LawModel.pdf_bytes.isnot(None))
        ).scalars().all()
    )


def _law_row(law: Dict[str, Any]) -> LawModel:
    row = LawModel(id=law["id"])
    _apply_law(row, law)
    return row


def _apply_law(row: LawModel, law: Dict[str, Any]) -> None:
    row.api_slug = law.get("apiSlug", law["id"])
    row.title = law.get("title", "")
    row.year = int(law.get("year", 0))
    row.category = law.get("category", "")
    row.status = law.get("status", "")
    row.short_desc = law.get("shortDesc", "")
    row.data = law


# --- Simulator personas/rules ---------------------------------------------

def read_personas(db: Session) -> List[Dict[str, Any]]:
    rows = db.execute(
        select(PersonaModel).order_by(PersonaModel.position, PersonaModel.row_id)
    ).scalars().all()
    return [r.data for r in rows]


def replace_personas(db: Session, personas: List[Dict[str, Any]]) -> None:
    """Replace the entire persona set (used by import-commit and PUT /personas)."""
    db.query(PersonaModel).delete()
    for pos, p in enumerate(personas):
        db.add(
            PersonaModel(
                persona_id=p["id"],
                law_id=p.get("lawId", ""),
                label=p.get("label", ""),
                position=pos,
                data=p,
            )
        )
    db.commit()


# --- Static content -------------------------------------------------------

def read_site(db: Session) -> Dict[str, Any]:
    row = db.get(SiteContentModel, "site")
    return row.data if row else {}


def read_navigation(db: Session) -> List[Dict[str, Any]]:
    row = db.get(SiteContentModel, "navigation")
    return row.data if row else []


def upsert_content(db: Session, key: str, data: Any) -> None:
    row = db.get(SiteContentModel, key)
    if row is None:
        db.add(SiteContentModel(key=key, data=data))
    else:
        row.data = data
    db.commit()


# --- Admin users ----------------------------------------------------------

def get_admin(db: Session, email: str) -> Optional[AdminUserModel]:
    row = db.get(AdminUserModel, email.lower())
    return row if row and row.is_active else None


def upsert_admin(db: Session, email: str, password_hash: str) -> None:
    row = db.get(AdminUserModel, email.lower())
    if row is None:
        db.add(AdminUserModel(email=email.lower(), password_hash=password_hash))
    else:
        row.password_hash = password_hash
    db.commit()
