"""Static site content (footer, brand, navigation) and categories."""
from __future__ import annotations

from typing import Any, Dict, List

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.schemas.common import NavLink
from app.services import store

router = APIRouter(tags=["content"])

# Ported from src/constants/index.ts
CATEGORIES = [
    "All",
    "Data Protection",
    "Cyber Law",
    "Consumer",
    "Corporate",
    "Governance",
    "Financial",
]


@router.get("/site")
def get_site(db: Session = Depends(get_db)) -> Dict[str, Any]:
    return store.read_site(db)


@router.get("/navigation", response_model=List[NavLink])
def get_navigation(db: Session = Depends(get_db)) -> List[NavLink]:
    return [NavLink(**n) for n in store.read_navigation(db)]


@router.get("/categories", response_model=List[str])
def get_categories() -> List[str]:
    return CATEGORIES
