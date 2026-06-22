"""Admin API — protected CRUD for laws + simulator rules, stats, rule import.

All routes require a valid admin bearer token.
"""
from __future__ import annotations

from typing import List

from fastapi import APIRouter, Depends, File, HTTPException, Response, UploadFile
from sqlalchemy.orm import Session

from app.api.deps import get_current_admin
from app.core.database import get_db
from app.schemas.common import AdminStats, ImportCommitResult, ImportPreview
from app.schemas.law import Law, LawCreate, LawUpdate
from app.schemas.simulator import Persona
from app.services import store
from app.services.law_builder import build_law
from app.services.rule_import import (
    build_template_workbook,
    merge_personas,
    parse_rows,
    workbook_to_rows,
)

router = APIRouter(
    prefix="/admin",
    tags=["admin"],
    dependencies=[Depends(get_current_admin)],
)


# --- Stats (ports adminStats.ts) ------------------------------------------

@router.get("/stats", response_model=AdminStats)
def get_stats(db: Session = Depends(get_db)) -> AdminStats:
    laws = [Law(**l) for l in store.read_laws(db)]
    personas = [Persona(**p) for p in store.read_personas(db)]
    rules = [r for p in personas for t in p.triggers for r in t.rules]
    return AdminStats(
        laws=len(laws),
        provisions=sum(len(l.provisions) for l in laws),
        personas=len(personas),
        triggers=sum(len(p.triggers) for p in personas),
        rules=len(rules),
        mandatoryRules=sum(1 for r in rules if r.tier == "mandatory"),
        recommendedRules=sum(1 for r in rules if r.tier == "recommended"),
        totalPenaltyExposure=sum(r.penalty for r in rules),
        inForceLaws=sum(1 for l in laws if l.status == "In force"),
    )


# --- Laws CRUD ------------------------------------------------------------

@router.post("/laws", response_model=Law, status_code=201)
def create_law(payload: LawCreate, db: Session = Depends(get_db)) -> Law:
    law = build_law(payload, store.get_law_id_set(db))
    store.insert_law(db, law.model_dump())
    return law


@router.put("/laws/{law_id}", response_model=Law)
def update_law(law_id: str, payload: LawUpdate, db: Session = Depends(get_db)) -> Law:
    current_raw = store.find_law(db, law_id)
    if current_raw is None or current_raw.get("id") != law_id:
        # find_law also matches by apiSlug; require an id match for updates.
        existing = next((l for l in store.read_laws(db) if l["id"] == law_id), None)
        if existing is None:
            raise HTTPException(status_code=404, detail=f"Law '{law_id}' not found.")
        current_raw = existing
    current = Law(**current_raw)
    merged = current.model_copy(update=payload.model_dump(exclude_unset=True))
    updated = store.update_law(db, law_id, merged.model_dump())
    if updated is None:
        raise HTTPException(status_code=404, detail=f"Law '{law_id}' not found.")
    return Law(**updated)


@router.delete("/laws/{law_id}", status_code=204)
def delete_law(law_id: str, db: Session = Depends(get_db)) -> Response:
    if not store.delete_law(db, law_id):
        raise HTTPException(status_code=404, detail=f"Law '{law_id}' not found.")
    return Response(status_code=204)


# --- Law PDF upload (official gazette copy) --------------------------------

@router.put("/laws/{law_id}/pdf", status_code=204)
def upload_law_pdf(
    law_id: str,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
) -> Response:
    """Upload (or replace) the official PDF for a law. Served via the public
    /laws/{slug}/pdf endpoint and the 'Access this law' panel."""
    content = file.file.read()
    if not content:
        raise HTTPException(status_code=400, detail="Empty file.")
    ctype = (file.content_type or "").lower()
    name = (file.filename or "").lower()
    if "pdf" not in ctype and not name.endswith(".pdf"):
        raise HTTPException(status_code=400, detail="File must be a PDF.")
    if not store.set_law_pdf(db, law_id, content, file.filename or f"{law_id}.pdf"):
        raise HTTPException(status_code=404, detail=f"Law '{law_id}' not found.")
    return Response(status_code=204)


@router.delete("/laws/{law_id}/pdf", status_code=204)
def remove_law_pdf(law_id: str, db: Session = Depends(get_db)) -> Response:
    """Remove an uploaded PDF (the public endpoint falls back to a generated one)."""
    if not store.delete_law_pdf(db, law_id):
        raise HTTPException(
            status_code=404, detail=f"No uploaded PDF for law '{law_id}'."
        )
    return Response(status_code=204)


# --- Simulator rules: read + replace --------------------------------------

@router.get("/personas", response_model=List[Persona])
def list_personas(db: Session = Depends(get_db)) -> List[Persona]:
    return [Persona(**p) for p in store.read_personas(db)]


@router.put("/personas", response_model=List[Persona])
def replace_personas(personas: List[Persona], db: Session = Depends(get_db)) -> List[Persona]:
    store.replace_personas(db, [p.model_dump() for p in personas])
    return personas


# --- Rule import (ports ruleImport.ts) ------------------------------------

@router.get("/rules/template")
def download_template() -> Response:
    content = build_template_workbook()
    return Response(
        content=content,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={
            "Content-Disposition": 'attachment; filename="simulator-rules-template.xlsx"'
        },
    )


def _parse_upload(file: UploadFile, db: Session) -> tuple:
    content = file.file.read()
    try:
        rows = workbook_to_rows(content)
    except Exception as exc:  # noqa: BLE001 - surface a clean 400
        raise HTTPException(status_code=400, detail=f"Could not read file: {exc}") from exc
    incoming, rule_count, issues = parse_rows(rows)
    if rule_count == 0 and not issues:
        raise HTTPException(
            status_code=400,
            detail="No rule rows found. Use the template and fill at least one row.",
        )
    existing = [Persona(**p) for p in store.read_personas(db)]
    merged, added, updated = merge_personas(existing, incoming)
    return incoming, rule_count, issues, merged, added, updated


@router.post("/rules/preview", response_model=ImportPreview)
def preview_import(
    file: UploadFile = File(...), db: Session = Depends(get_db)
) -> ImportPreview:
    """Parse + merge an uploaded .xlsx WITHOUT persisting — for a dry-run preview."""
    incoming, rule_count, issues, merged, added, updated = _parse_upload(file, db)
    return ImportPreview(
        personas=incoming,
        ruleCount=rule_count,
        issues=issues,
        added=added,
        updated=updated,
        totalPersonas=len(merged),
    )


@router.post("/rules/import", response_model=ImportCommitResult)
def commit_import(
    file: UploadFile = File(...), db: Session = Depends(get_db)
) -> ImportCommitResult:
    """Parse, merge, and PERSIST imported rules into the database."""
    _, rule_count, issues, merged, added, updated = _parse_upload(file, db)
    store.replace_personas(db, [p.model_dump() for p in merged])
    return ImportCommitResult(
        ruleCount=rule_count,
        issues=issues,
        added=added,
        updated=updated,
        totalPersonas=len(merged),
    )
