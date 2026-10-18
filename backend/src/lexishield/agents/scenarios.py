"""What-if scenarios over the stored triage report.

Scenario descriptions are data (backend/scenarios/*.yaml). The arithmetic runs only on facts extracted from verified
quotes in the report, and every exposure component cites the quote its amount came from. If a needed number is not
stated, the result says so in missing_inputs and sets computable to false. Nothing is estimated or assumed.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Any

import yaml

from ..models import (
    ChecklistItem,
    ChecklistStatus,
    Citation,
    ClaimKind,
    Escalation,
    Exposure,
    ExposureComponent,
    ScenarioInfo,
    ScenarioResult,
    ScenarioStep,
    TriageReport,
)
from ..settings import Settings, get_settings
from ..verify.facts import extract_facts

STATED = {ChecklistStatus.ENTAILED, ChecklistStatus.CONTRADICTED}
FAMILY = {"rental": "rent_tenancy", "employment": "employment"}


class ScenarioNotFound(KeyError):
    pass


@lru_cache
def load_scenarios(directory: str) -> dict[str, ScenarioInfo]:
    out: dict[str, ScenarioInfo] = {}
    for path in sorted(Path(directory).glob("*.yaml")):
        info = ScenarioInfo.model_validate(yaml.safe_load(path.read_text(encoding="utf-8")))
        if info.scenario_id != path.stem:
            raise ValueError(f"{path.name}: scenario_id must match the file name")
        out[info.scenario_id] = info
    return out


def all_scenarios(settings: Settings | None = None) -> dict[str, ScenarioInfo]:
    return load_scenarios(str((settings or get_settings()).paths.resolve("scenarios_dir")))


@dataclass(frozen=True)
class Fact:
    unit: str
    value: float
    citation: Citation


def _item(report: TriageReport, topic_id: str) -> ChecklistItem | None:
    return next((i for i in report.checklist if i.topic_id == topic_id), None)


def _facts(report: TriageReport, topic_id: str) -> list[Fact]:
    """Numeric facts from the verified quotes of a topic the document states. Silent or unclear topics give none."""
    item = _item(report, topic_id)
    if item is None or item.status not in STATED:
        return []
    out: list[Fact] = []
    for cit in item.evidence:
        for fact in sorted(extract_facts(cit.quote)):
            unit, _, raw = fact.rpartition(" ")
            try:
                out.append(Fact(unit, float(raw), cit))
            except ValueError:
                continue  # dates are not numeric
    return out


def _first(facts: list[Fact], unit: str) -> Fact | None:
    return next((f for f in facts if f.unit == unit), None)


def _silent(report: TriageReport, topic_id: str) -> bool:
    item = _item(report, topic_id)
    return item is not None and item.status == ChecklistStatus.NOT_MENTIONED


def _money(value: float) -> str:
    return f"Rs. {value:,.0f}"


def _escalation(report: TriageReport, doc_type: str) -> Escalation | None:
    family = FAMILY.get(doc_type)
    return next((e for e in report.escalations if e.topic_family == family), None)


def _exposure(components: list[ExposureComponent], missing: list[str]) -> Exposure:
    if missing:
        return Exposure(computable=False, components=components, missing_inputs=missing)
    return Exposure(
        computable=True,
        total=sum(c.amount for c in components),
        currency="INR" if components else None,
        components=components,
    )


def _months_param(params: dict[str, Any], name: str) -> int | None:
    value = params.get(name)
    return value if isinstance(value, int) and not isinstance(value, bool) and value >= 0 else None


def rental_early_exit(report: TriageReport, params: dict[str, Any]) -> tuple[list[ScenarioStep], Exposure, list[str]]:
    steps: list[ScenarioStep] = []
    missing: list[str] = []
    components: list[ExposureComponent] = []
    silences: list[str] = []
    months = _months_param(params, "months_stayed")
    if months is None:
        steps.append(
            ScenarioStep(
                text="Tell me how many months into the agreement you would leave.", kind=ClaimKind.INTERPRETATION
            )
        )
        return steps, _exposure([], ["months_stayed"]), silences

    lock = _first(_facts(report, "in_rental.lock_in"), "months")
    if lock is not None:
        steps.append(
            ScenarioStep(
                text=f"The agreement has a lock-in of {lock.value:.0f} months.",
                kind=ClaimKind.STATED,
                citations=[lock.citation],
            )
        )
        if months < lock.value:
            steps.append(
                ScenarioStep(
                    text=f"Leaving after {months} months falls inside the lock-in. The document does not state an "
                    "amount for leaving during the lock-in, so none is added.",
                    kind=ClaimKind.INTERPRETATION,
                    citations=[lock.citation],
                )
            )
            missing.append("charge for leaving during the lock-in (no amount is stated)")
    elif _silent(report, "in_rental.lock_in"):
        silences.append("in_rental.lock_in")
        steps.append(ScenarioStep(text="The document does not mention a lock-in period.", kind=ClaimKind.STATED))

    notice_facts = _facts(report, "in_rental.termination_notice")
    notice_months = _first(notice_facts, "months")
    notice_days = _first(notice_facts, "days")
    rent = _first(_facts(report, "in_rental.rent_amount"), "INR")
    if notice_months is not None:
        steps.append(
            ScenarioStep(
                text=f"The notice period is {notice_months.value:.0f} months.",
                kind=ClaimKind.STATED,
                citations=[notice_months.citation],
            )
        )
    elif notice_days is not None:
        steps.append(
            ScenarioStep(
                text=f"The notice period is {notice_days.value:.0f} days.",
                kind=ClaimKind.STATED,
                citations=[notice_days.citation],
            )
        )
        missing.append("rent for a notice period stated in days (not converted to months, to avoid guessing)")
    else:
        missing.append("notice period (not stated as a number)")
    if rent is None:
        missing.append("monthly rent (not stated as an amount)")
    if notice_months is not None and rent is not None:
        amount = rent.value * notice_months.value
        components.append(
            ExposureComponent(
                label=f"Rent for the {notice_months.value:.0f}-month notice period, if you pay through it",
                amount=amount,
                currency="INR",
                citation=rent.citation,
            )
        )
        steps.append(
            ScenarioStep(
                text=f"Rent of {_money(rent.value)} for {notice_months.value:.0f} months of notice is "
                f"{_money(amount)}.",
                kind=ClaimKind.INTERPRETATION,
                citations=[rent.citation, notice_months.citation],
            )
        )
    return steps, _exposure(components, missing), silences


def deposit_refund(report: TriageReport, params: dict[str, Any]) -> tuple[list[ScenarioStep], Exposure, list[str]]:
    steps: list[ScenarioStep] = []
    missing: list[str] = []
    components: list[ExposureComponent] = []
    silences: list[str] = []
    deposit = _first(_facts(report, "in_rental.security_deposit"), "INR")
    if deposit is None:
        missing.append("deposit amount (not stated as an amount)")
    else:
        steps.append(
            ScenarioStep(
                text=f"The deposit is {_money(deposit.value)}.", kind=ClaimKind.STATED, citations=[deposit.citation]
            )
        )
        components.append(
            ExposureComponent(label="Deposit at stake", amount=deposit.value, currency="INR", citation=deposit.citation)
        )

    refund = _facts(report, "in_rental.deposit_refund_deductions")
    timeline = _first(refund, "days") or _first(refund, "months")
    if timeline is not None:
        steps.append(
            ScenarioStep(
                text=f"The document says it is returned within {timeline.value:.0f} {timeline.unit}.",
                kind=ClaimKind.STATED,
                citations=[timeline.citation],
            )
        )
    elif _silent(report, "in_rental.deposit_refund_deductions"):
        silences.append("in_rental.deposit_refund_deductions")
        steps.append(
            ScenarioStep(text="The document does not say when the deposit is returned.", kind=ClaimKind.STATED)
        )

    deductions = _item(report, "in_rental.painting_cleaning_deductions")
    if deductions is not None and deductions.status in STATED and deductions.evidence:
        steps.append(
            ScenarioStep(
                text="The document lists charges that can be deducted. Read the quoted clause.",
                kind=ClaimKind.STATED,
                citations=deductions.evidence,
            )
        )
    return steps, _exposure(components, missing), silences


def bond_exit(report: TriageReport, params: dict[str, Any]) -> tuple[list[ScenarioStep], Exposure, list[str]]:
    steps: list[ScenarioStep] = []
    missing: list[str] = []
    components: list[ExposureComponent] = []
    silences: list[str] = []
    served = _months_param(params, "months_served")
    if served is None:
        steps.append(
            ScenarioStep(
                text="Tell me how many months you would have worked when you leave.", kind=ClaimKind.INTERPRETATION
            )
        )
        return steps, _exposure([], ["months_served"]), silences

    bond = _facts(report, "in_employment.service_bond")
    period = _first(bond, "months")
    amount = _first(bond, "INR")
    if period is None and amount is None and _silent(report, "in_employment.service_bond"):
        silences.append("in_employment.service_bond")
        steps.append(ScenarioStep(text="The document does not mention a bond or a repayment.", kind=ClaimKind.STATED))
        return steps, _exposure([], []), silences
    if period is None:
        missing.append("bond period (not stated in months)")
    if amount is None:
        missing.append("bond repayment amount (not stated as an amount)")
    if period is not None:
        steps.append(
            ScenarioStep(
                text=f"The bond period is {period.value:.0f} months.",
                kind=ClaimKind.STATED,
                citations=[period.citation],
            )
        )
    if period is not None and amount is not None:
        if served < period.value:
            steps.append(
                ScenarioStep(
                    text=f"Leaving after {served} months is inside the bond period, so the stated repayment of "
                    f"{_money(amount.value)} applies.",
                    kind=ClaimKind.INTERPRETATION,
                    citations=[period.citation, amount.citation],
                )
            )
            components.append(
                ExposureComponent(label="Bond repayment", amount=amount.value, currency="INR", citation=amount.citation)
            )
        else:
            steps.append(
                ScenarioStep(
                    text=f"Leaving after {served} months is after the bond period, so the bond repayment does "
                    "not apply.",
                    kind=ClaimKind.INTERPRETATION,
                    citations=[period.citation],
                )
            )

    notice = _first(_facts(report, "in_employment.notice_period"), "days")
    if notice is not None:
        steps.append(
            ScenarioStep(
                text=f"You must give {notice.value:.0f} days notice.",
                kind=ClaimKind.STATED,
                citations=[notice.citation],
            )
        )
    return steps, _exposure(components, missing), silences


ENGINES: dict[str, Callable[[TriageReport, dict[str, Any]], tuple[list[ScenarioStep], Exposure, list[str]]]] = {
    "rental_early_exit": rental_early_exit,
    "deposit_refund": deposit_refund,
    "bond_exit": bond_exit,
}


class ScenarioNotApplicable(ValueError):
    pass


def run_scenario(
    scenario_id: str, report: TriageReport, params: dict[str, Any], settings: Settings | None = None
) -> ScenarioResult:
    info = all_scenarios(settings).get(scenario_id)
    engine = ENGINES.get(scenario_id)
    if info is None or engine is None:
        raise ScenarioNotFound(scenario_id)
    doc_type = report.classification.doc_type
    if doc_type not in info.doc_types:
        raise ScenarioNotApplicable(f"{info.title} applies to {', '.join(d.value for d in info.doc_types)} documents.")
    steps, exposure, silences = engine(report, params)
    return ScenarioResult(
        scenario_id=scenario_id,
        title=info.title,
        steps=steps,
        exposure=exposure,
        silences=silences,
        escalation=_escalation(report, doc_type.value),
    )
