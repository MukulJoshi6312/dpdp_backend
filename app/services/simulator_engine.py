"""Compliance simulator evaluation — 1:1 port of frontend src/lib/simulator.ts."""
from __future__ import annotations

from typing import List, Set

from app.schemas.simulator import (
    ComplianceRule,
    RuleResult,
    RuleStatus,
    SimulatorResult,
)


def _round_half_up(value: float) -> int:
    """Match JavaScript's Math.round (round half away from zero for positives)."""
    import math

    return int(math.floor(value + 0.5))


def item_key(rule_id: str, kind: str, index: int) -> str:
    """Build the unique checklist-item key for a rule item ('action'/'artifact')."""
    return f"{rule_id}::{kind}::{index}"


def _evaluate_rule(rule: ComplianceRule, checked: Set[str]) -> RuleResult:
    total = len(rule.actions) + len(rule.artifacts)

    missing_actions = [
        a for i, a in enumerate(rule.actions)
        if item_key(rule.id, "action", i) not in checked
    ]
    missing_artifacts = [
        a for i, a in enumerate(rule.artifacts)
        if item_key(rule.id, "artifact", i) not in checked
    ]

    checked_count = total - len(missing_actions) - len(missing_artifacts)
    percent = 100 if total == 0 else _round_half_up((checked_count / total) * 100)

    if checked_count == 0:
        status: RuleStatus = "non-compliant"
    elif checked_count == total:
        status = "compliant"
    else:
        status = "partial"

    return RuleResult(
        rule=rule,
        status=status,
        total=total,
        checked=checked_count,
        percent=percent,
        missingActions=missing_actions,
        missingArtifacts=missing_artifacts,
    )


def _risk_level_for(overall_percent: int, non_compliant: int, applicable: int) -> str:
    if applicable == 0:
        return "Compliant"
    if overall_percent == 100:
        return "Compliant"
    if non_compliant == applicable:
        return "Critical Risk"
    if overall_percent < 34:
        return "High Risk"
    if overall_percent < 67:
        return "Moderate Risk"
    return "Low Risk"


def compute_result(rules: List[ComplianceRule], checked_keys: Set[str]) -> SimulatorResult:
    """Evaluate every applicable rule against the set of checked item keys."""
    per_rule = [_evaluate_rule(r, checked_keys) for r in rules]

    compliant = sum(1 for r in per_rule if r.status == "compliant")
    partial = sum(1 for r in per_rule if r.status == "partial")
    non_compliant = sum(1 for r in per_rule if r.status == "non-compliant")

    total_items = sum(r.total for r in per_rule)
    checked_items = sum(r.checked for r in per_rule)
    overall_percent = 100 if total_items == 0 else _round_half_up((checked_items / total_items) * 100)

    at_risk = [r for r in per_rule if r.status != "compliant"]
    total_exposure = sum(r.rule.penalty for r in at_risk)

    return SimulatorResult(
        perRule=per_rule,
        applicable=len(rules),
        compliant=compliant,
        partial=partial,
        nonCompliant=non_compliant,
        overallPercent=overall_percent,
        totalExposure=total_exposure,
        rulesAtRisk=len(at_risk),
        riskLevel=_risk_level_for(overall_percent, non_compliant, len(rules)),
    )
