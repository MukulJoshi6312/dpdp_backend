"""Create tables and seed the database from the bundled JSON files.

Usage:
    python -m app.seed            # create tables + seed if empty
    python -m app.seed --reset    # drop all tables, recreate, reseed
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

from sqlalchemy import select

from app.core.config import settings
from app.core.database import Base, SessionLocal, engine
from app.core.security import hash_password
from app.models.db_models import (  # noqa: F401 - register models on Base
    AdminUserModel,
    LawModel,
    PersonaModel,
    SiteContentModel,
)
from app.services import store

_DATA_DIR = Path(__file__).resolve().parent / settings.data_dir


def _load(name: str):
    with (_DATA_DIR / name).open("r", encoding="utf-8") as fh:
        return json.load(fh)


def create_tables() -> None:
    Base.metadata.create_all(bind=engine)


def drop_tables() -> None:
    Base.metadata.drop_all(bind=engine)


def seed() -> None:
    db = SessionLocal()
    try:
        # Laws
        if db.execute(select(LawModel.id)).first() is None:
            for law in _load("laws.json"):
                store.insert_law(db, law)
            print(f"  seeded laws")
        else:
            print("  laws already present — skipping")

        # Personas / simulator rules
        if db.execute(select(PersonaModel.row_id)).first() is None:
            store.replace_personas(db, _load("simulator-rules.json"))
            print("  seeded personas")
        else:
            print("  personas already present — skipping")

        # Static content
        store.upsert_content(db, "site", _load("site.json"))
        store.upsert_content(db, "navigation", _load("navigation.json"))
        print("  seeded site + navigation")

        # Admin user
        if db.get(AdminUserModel, settings.admin_email.lower()) is None:
            store.upsert_admin(
                db, settings.admin_email, hash_password(settings.admin_password)
            )
            print(f"  seeded admin user: {settings.admin_email}")
        else:
            print("  admin user already present — skipping")
    finally:
        db.close()


def main() -> None:
    reset = "--reset" in sys.argv
    if reset:
        print("Dropping all tables…")
        drop_tables()
    print("Creating tables…")
    create_tables()
    print("Seeding…")
    seed()
    print("Done.")


if __name__ == "__main__":
    main()
