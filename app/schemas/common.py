"""Shared / misc schemas (site content, stats, rule import)."""
from __future__ import annotations

from typing import List

from pydantic import BaseModel, Field

from app.schemas.simulator import Persona


class NavLink(BaseModel):
    href: str
    label: str


class AdminStats(BaseModel):
    laws: int
    provisions: int
    personas: int
    triggers: int
    rules: int
    mandatoryRules: int
    recommendedRules: int
    totalPenaltyExposure: float
    inForceLaws: int


class ImportIssue(BaseModel):
    row: int
    message: str


class ImportPreview(BaseModel):
    """Result of parsing+merging an uploaded rules spreadsheet, without committing."""
    personas: List[Persona]
    ruleCount: int
    issues: List[ImportIssue]
    added: int
    updated: int
    totalPersonas: int


class ImportCommitResult(BaseModel):
    ruleCount: int
    issues: List[ImportIssue]
    added: int
    updated: int
    totalPersonas: int
    committed: bool = True
