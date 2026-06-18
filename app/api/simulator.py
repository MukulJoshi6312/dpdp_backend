"""Compliance simulator API.

    GET  /v1/simulator/personas
    GET  /v1/simulator/personas/{persona_id}
    POST /v1/simulator/evaluate
"""
from __future__ import annotations

from typing import List

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.schemas.simulator import Persona, SimulateRequest, SimulatorResult
from app.services import store
from app.services.simulator_engine import compute_result

router = APIRouter(prefix="/simulator", tags=["simulator"])


def _personas(db: Session) -> List[Persona]:
    return [Persona(**raw) for raw in store.read_personas(db)]


@router.get("/personas", response_model=List[Persona])
def list_personas(db: Session = Depends(get_db)) -> List[Persona]:
    return _personas(db)


@router.get("/personas/{persona_id}", response_model=Persona)
def get_persona(persona_id: str, db: Session = Depends(get_db)) -> Persona:
    for p in _personas(db):
        if p.id == persona_id:
            return p
    raise HTTPException(status_code=404, detail=f"Persona '{persona_id}' not found.")


@router.post("/evaluate", response_model=SimulatorResult)
def evaluate(req: SimulateRequest, db: Session = Depends(get_db)) -> SimulatorResult:
    """Evaluate the rules of one persona+trigger against checked checklist items."""
    persona = next((p for p in _personas(db) if p.id == req.personaId), None)
    if persona is None:
        raise HTTPException(status_code=404, detail=f"Persona '{req.personaId}' not found.")

    trigger = next((t for t in persona.triggers if t.id == req.triggerId), None)
    if trigger is None:
        raise HTTPException(
            status_code=404,
            detail=f"Trigger '{req.triggerId}' not found for persona '{req.personaId}'.",
        )

    return compute_result(trigger.rules, set(req.checkedKeys))
