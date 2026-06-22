"""Public laws API.

Mirrors the contract advertised in the frontend ApiPanel:
    GET /v1/laws
    GET /v1/laws/{slug}
    GET /v1/laws/{slug}/penalties
    GET /v1/laws/{slug}/provisions
    GET /v1/laws/{slug}/provisions/{provision_slug}
"""
from __future__ import annotations

import re
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Response
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.schemas.law import Law, Penalty, Provision
from app.services import store
from app.services.exporters import law_to_pdf, law_to_xml, reportlab_available

router = APIRouter(prefix="/laws", tags=["laws"])


def _provision_slug(num: str) -> str:
    """Slug used in mock REST samples (ports helpers.provisionSlug)."""
    return re.sub(r"[^0-9A-Za-z]", "", num).lower()


def _find_law(db: Session, slug: str) -> Law:
    raw = store.find_law(db, slug)
    if raw is None:
        raise HTTPException(status_code=404, detail=f"Law '{slug}' not found.")
    law = Law(**raw)
    law.hasPdf = store.law_has_pdf(db, slug)
    return law


@router.get("", response_model=List[Law])
def list_laws(
    category: Optional[str] = Query(None, description="Filter by category (exact)."),
    q: Optional[str] = Query(None, description="Search title / description / authority."),
    status: Optional[str] = Query(None, description="Filter by status, e.g. 'In force'."),
    db: Session = Depends(get_db),
) -> List[Law]:
    laws = [Law(**raw) for raw in store.read_laws(db)]
    if category and category.lower() != "all":
        laws = [l for l in laws if l.category.lower() == category.lower()]
    if status:
        laws = [l for l in laws if l.status.lower() == status.lower()]
    if q:
        needle = q.lower()
        laws = [
            l for l in laws
            if needle in l.title.lower()
            or needle in l.shortDesc.lower()
            or needle in l.authority.lower()
        ]
    with_pdf = store.law_ids_with_pdf(db)
    for l in laws:
        l.hasPdf = l.id in with_pdf
    return laws


@router.get("/{slug}", response_model=Law)
def get_law(slug: str, db: Session = Depends(get_db)) -> Law:
    return _find_law(db, slug)


@router.get("/{slug}/xml")
def get_law_xml(slug: str, db: Session = Depends(get_db)) -> Response:
    """Download the law as structured XML (simplified LegalDocML)."""
    law = _find_law(db, slug)
    return Response(
        content=law_to_xml(law),
        media_type="application/xml",
        headers={
            "Content-Disposition": f'attachment; filename="{law.apiSlug}.xml"'
        },
    )


@router.get("/{slug}/pdf")
def get_law_pdf(slug: str, db: Session = Depends(get_db)) -> Response:
    """Serve the law as a PDF.

    Prefers the uploaded official PDF (the actual gazette copy). If none was
    uploaded, falls back to a generated informational copy via reportlab.
    """
    law = _find_law(db, slug)

    uploaded = store.get_law_pdf(db, slug)
    if uploaded is not None:
        content, filename = uploaded
        return Response(
            content=content,
            media_type="application/pdf",
            headers={"Content-Disposition": f'attachment; filename="{filename}"'},
        )

    if not reportlab_available():
        raise HTTPException(
            status_code=503,
            detail="No PDF uploaded and PDF generation is unavailable — "
            "upload a PDF in the admin Laws screen or install reportlab.",
        )
    return Response(
        content=law_to_pdf(law),
        media_type="application/pdf",
        headers={
            "Content-Disposition": f'attachment; filename="{law.apiSlug}.pdf"'
        },
    )


@router.get("/{slug}/penalties", response_model=List[Penalty])
def get_law_penalties(slug: str, db: Session = Depends(get_db)) -> List[Penalty]:
    return _find_law(db, slug).penalties


@router.get("/{slug}/provisions", response_model=List[Provision])
def get_law_provisions(slug: str, db: Session = Depends(get_db)) -> List[Provision]:
    return _find_law(db, slug).provisions


@router.get("/{slug}/provisions/{provision_slug}", response_model=Provision)
def get_law_provision(
    slug: str, provision_slug: str, db: Session = Depends(get_db)
) -> Provision:
    law = _find_law(db, slug)
    for p in law.provisions:
        if _provision_slug(p.num) == provision_slug.lower():
            return p
    raise HTTPException(
        status_code=404,
        detail=f"Provision '{provision_slug}' not found in law '{slug}'.",
    )
