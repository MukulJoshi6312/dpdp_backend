"""Admin authentication — replaces the frontend's demo localStorage session."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_admin
from app.core.database import get_db
from app.core.security import create_access_token
from app.schemas.auth import AdminProfile, LoginRequest, TokenResponse
from app.services.admin_user import authenticate

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/login", response_model=TokenResponse)
def login(payload: LoginRequest, db: Session = Depends(get_db)) -> TokenResponse:
    email = authenticate(db, payload.email, payload.password)
    if email is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password.",
        )
    token = create_access_token(subject=email)
    return TokenResponse(access_token=token, email=email)


@router.get("/me", response_model=AdminProfile)
def me(email: str = Depends(get_current_admin)) -> AdminProfile:
    return AdminProfile(email=email)
