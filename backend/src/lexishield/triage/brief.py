"""Pre-lawyer brief, built only from the stored report (no model call). JSON for the app, Markdown to print or share.

Top issues are the cards that most need a professional: ASK_A_LAWYER first, then INTERPRETATION, then by severity.
Deadlines are explanations that state a time limit. Everything shown here already passed the verification gate.
"""

from __future__ import annotations

from datetime import UTC, datetime

from ..models import Claim, ClauseCard, EscalationBrief, Severity, Tier, TriageReport

TOP_ISSUES = 5
MAX_QUESTIONS = 8
TIER_ORDER = {Tier.ASK_A_LAWYER: 0, Tier.INTERPRETATION: 1, Tier.STATED: 2, Tier.NOT_FOUND: 3}
SEVERITY_ORDER = {Severity.HIGH: 0, Severity.MEDIUM: 1, Severity.LOW: 2, Severity.INFO: 3}
TIME_UNITS = ("days ", "months ", "years ", "weeks ", "date ")


def _is_deadline(claim: Claim | None) -> bool:
    return claim is not None and any(f.startswith(TIME_UNITS) for f in claim.facts)


def build_brief(report: TriageReport) -> EscalationBrief:
    cards = sorted(report.cards, key=lambda c: (TIER_ORDER[c.tier], SEVERITY_ORDER[c.severity]))
    top = [c for c in cards if c.tier != Tier.STATED or c.severity == Severity.HIGH][:TOP_ISSUES]
    questions: list[str] = []
    for card in cards:
        for q in card.questions_for_lawyer:
            if q not in questions:
                questions.append(q)
    return EscalationBrief(
        document_id=report.document_id,
        generated_at=datetime.now(UTC),
        doc_type=report.classification.doc_type,
        jurisdiction=report.jurisdiction,
        parties=report.classification.party_roles,
        top_issues=top,
        deadlines=[c.plain_explanation for c in report.cards if _is_deadline(c.plain_explanation)],  # type: ignore[misc]
        silences=report.silences,
        questions_for_lawyer=questions[:MAX_QUESTIONS],
        escalations=report.escalations,
    )


def _card_md(card: ClauseCard) -> list[str]:
    lines = [f"### {card.title} ({card.severity.value.lower()}, {card.tier.value.replace('_', ' ').lower()})"]
    if card.source is not None:
        lines.append(f"> {card.source.quote}  \n> (clause {card.source.clause_id}, page {card.source.page})")
    if card.plain_explanation is not None:
        lines.append(card.plain_explanation.text)
    elif card.explanation_withheld_reason:
        lines.append(f"_{card.explanation_withheld_reason}_")
    lines += [f"- Unclear: {a}" for a in card.ambiguity_flags]
    return lines


def render_markdown(brief: EscalationBrief) -> str:
    out = [
        "# Brief for a lawyer",
        "",
        f"Document type: {brief.doc_type.value}. Jurisdiction: {brief.jurisdiction.country.value}"
        + (f" ({brief.jurisdiction.state})" if brief.jurisdiction.state else "")
        + ".",
    ]
    if brief.parties:
        out += ["", "Parties: " + "; ".join(f"{name} ({role.value})" for name, role in brief.parties.items())]
    if brief.top_issues:
        out += ["", "## Issues to discuss", ""]
        for card in brief.top_issues:
            out += _card_md(card) + [""]
    if brief.deadlines:
        out += ["## Time limits stated in the document", ""] + [f"- {c.text}" for c in brief.deadlines] + [""]
    if brief.silences:
        out += ["## What the document does not say", ""] + [f"- {s}" for s in brief.silences] + [""]
    if brief.questions_for_lawyer:
        out += ["## Questions to ask", ""] + [f"- {q}" for q in brief.questions_for_lawyer] + [""]
    if brief.escalations:
        out += ["## Who can help", ""]
        for e in brief.escalations:
            line = f"- {e.who}: {e.why}"
            if e.free_help:
                line += f" Free help: {e.free_help}."
            if e.urgency == "urgent":
                line += " Urgent."
            out.append(line)
        out.append("")
    out += ["---", brief.disclaimer, ""]
    return "\n".join(out)
