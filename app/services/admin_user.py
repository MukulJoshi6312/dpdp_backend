"""Admin authentication against the admin_users table."""
from __future__ import annotations

from typing import Optional

from sqlalchemy.orm import Session

from app.core.security import verify_password
from app.services import store


def authenticate(db: Session, email: str, password: str) -> Optional[str]:
    """Return the admin email if credentials are valid, else None."""
    admin = store.get_admin(db, email)
    if admin is None:
        return None
    if not verify_password(password, admin.password_hash):
        return None
    return admin.email
