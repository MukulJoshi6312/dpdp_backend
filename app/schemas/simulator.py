"""Schemas for the compliance simulator — mirrors the rules-engine types."""
from __future__ import annotations

from typing import List, Literal

from pydantic import BaseModel, Field

RuleTier = Literal["mandatory", "recommended"]
RuleStatus = Literal["compliant", "partial", "non-compliant"]
RiskLevel = Literal[
    "Compliant", "Low Risk", "Moderate Risk", "High Risk", "Critical Risk"
]


class ComplianceRule(BaseModel):
    id: str
    title: str
    tier: RuleTier
    clauses: List[str] = Field(default_factory=list)
    actions: List[str] = Field(default_factory=list)
    artifacts: List[str] = Field(default_factory=list)
    penalty: float
    penaltyBasis: str = ""
    penaltyRef: str = ""


class TriggerEvent(BaseModel):
    id: str
    label: str
    rules: List[ComplianceRule] = Field(default_factory=list)


class Persona(BaseModel):
    id: str
    label: str
    # The law this persona's rules belong to (e.g. PROGA). Used by the
    # simulator UI to drive the Law -> Persona -> Trigger cascade.
    lawId: str = ""
    lawLabel: str = ""
    triggers: List[TriggerEvent] = Field(default_factory=list)


# --- Simulator evaluation request/response (ports simulator.ts) -----------

class SimulateRequest(BaseModel):
    """Evaluate a set of applicable rules against checked checklist items.

    `checkedKeys` use the same format as the frontend's itemKey():
    "<ruleId>::action::<index>" or "<ruleId>::artifact::<index>".
    """
    personaId: str
    triggerId: str
    checkedKeys: List[str] = Field(default_factory=list)


class RuleResult(BaseModel):
    rule: ComplianceRule
    status: RuleStatus
    total: int
    checked: int
    percent: int
    missingActions: List[str]
    missingArtifacts: List[str]


class SimulatorResult(BaseModel):
    perRule: List[RuleResult]
    applicable: int
    compliant: int
    partial: int
    nonCompliant: int
    overallPercent: int
    totalExposure: float
    rulesAtRisk: int
    riskLevel: RiskLevel
