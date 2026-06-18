"""Application configuration, loaded from environment / .env."""
from __future__ import annotations

from functools import lru_cache
from typing import List

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_name: str = "Nyaykosh API"
    api_v1_prefix: str = "/v1"

    # CORS — the Next.js dev server runs on :3000 by default.
    cors_origins: List[str] = ["http://localhost:3000", "http://127.0.0.1:3000"]

    # --- Auth -------------------------------------------------------------
    # CHANGE THESE before any real deployment.
    secret_key: str = "change-me-in-production-please-use-a-long-random-string"
    access_token_expire_minutes: int = 60 * 12  # 12h
    jwt_algorithm: str = "HS256"

    # Seed admin credentials. Password is plain here only for the demo seed;
    # it is hashed on first load. Override via env in production.
    admin_email: str = "admin@nyaykosh.in"
    admin_password: str = "changeme123"

    # Seed JSON files (used to populate the DB on first run / `seed` command).
    data_dir: str = "data"

    # --- Database ---------------------------------------------------------
    # PostgreSQL connection (SQLAlchemy 2.0 + psycopg 3 driver).
    database_url: str = "postgresql+psycopg://mukulsharma@localhost:5432/nyaykosh"
    db_echo: bool = False


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
