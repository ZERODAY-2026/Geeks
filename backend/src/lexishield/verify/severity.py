"""Severity rules from the pack data. A rule matches on the final status, or on a fact taken from the verified quotes.

Rules are data (packs/*.yaml), not code. They state observations ("higher than often seen"), never legal conclusions.
The first rule that matches sets the severity; if none matches, the topic's default severity is kept.
"""

from __future__ import annotations

from pydantic import BaseModel, Field

from ..models import ChecklistStatus, Severity


class RuleWhen(BaseModel):
    status: ChecklistStatus | None = None
    fact_unit: str | None = Field(default=None, description="Unit of an extracted fact, e.g. months, days, INR, pct.")
    gt: float | None = None
    lt: float | None = None


class RuleThen(BaseModel):
    severity: Severity
    note: str | None = None


class SeverityRule(BaseModel):
    when: RuleWhen
    then: RuleThen


def _fact_values(facts: set[str]) -> list[tuple[str, float]]:
    """Facts look like 'months 11' or 'INR 150000'; dates are not numeric and are skipped."""
    out: list[tuple[str, float]] = []
    for fact in facts:
        unit, _, raw = fact.rpartition(" ")
        try:
            out.append((unit, float(raw)))
        except ValueError:
            continue
    return out


def _matches(when: RuleWhen, status: ChecklistStatus, values: list[tuple[str, float]]) -> bool:
    if when.status is not None and when.status != status:
        return False
    if when.fact_unit is None:
        return when.status is not None
    for unit, value in values:
        if unit != when.fact_unit:
            continue
        if when.gt is not None and value <= when.gt:
            continue
        if when.lt is not None and value >= when.lt:
            continue
        return True
    return False


def apply_rules(
    rules: list[SeverityRule], status: ChecklistStatus, facts: set[str], default: Severity
) -> tuple[Severity, str | None]:
    values = _fact_values(facts)
    for rule in rules:
        if _matches(rule.when, status, values):
            return rule.then.severity, rule.then.note
    return default, None
