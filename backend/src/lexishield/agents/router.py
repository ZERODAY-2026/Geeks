"""Intent router for Ask. Rules only, no model call, so a verdict question is declined before any model sees it.

Order matters: out-of-scope (including attempts to change the assistant's instructions) first, then legal verdicts,
then what-if scenarios. Everything else is a question about the document.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from enum import StrEnum


class Intent(StrEnum):
    DOCFACT = "DOCFACT"
    LEGAL_VERDICT = "LEGAL_VERDICT"
    SCENARIO = "SCENARIO"
    OUT_OF_SCOPE = "OUT_OF_SCOPE"


OUT_OF_SCOPE_RE = re.compile(
    r"\bignore (?:all |any |the )?(?:previous|prior|above|your) (?:instructions|rules)"
    r"|\b(?:reveal|show|print|repeat) (?:me )?(?:your|the) (?:system )?(?:prompt|instructions)"
    r"|\bsystem prompt\b"
    r"|\bwrite (?:me )?(?:a|an) (?:poem|song|story|essay|joke|program|script)\b"
    r"|\b(?:weather|stock price|share price|bitcoin|cricket score|recipe)\b"
    r"|\b(?:forge|fake|backdate|falsify)\b",
    re.IGNORECASE,
)

# Words that always ask for a legal conclusion.
VERDICT_WORDS_RE = re.compile(
    r"\b(?:enforceab\w*|unenforceab\w*|illegal|unlawful|lawful|legally binding|legally valid|void|voidable)\b",
    re.IGNORECASE,
)
# Patterns that ask for a judgment, an outcome or a recommendation.
VERDICT_PATTERNS_RE = re.compile(
    r"\b(?:is|are|was|would|will) (?:this|that|it|these|they|the|my|our)(?: [\w\-]+){0,4}? "
    r"(?:legal|valid|invalid|binding|fair|unfair|allowed by law|against the law)\b"
    r"|\b(?:can|could|will|would) (?:they|he|she|i|we|you|the [\w ]{1,30}?|my [\w ]{1,30}?) "
    r"(?:sue|be sued|take (?:me|them|him|her) to court)\b"
    r"|\b(?:will|would|can|could) (?:i|we) (?:win|lose)\b"
    r"|\b(?:should|must|shall) i (?:sign|accept|agree|refuse|reject|challenge)\b"
    r"|\b(?:safe|ok|okay|wise|good idea) to sign\b"
    r"|\bdo i have (?:a|any) (?:case|claim)\b"
    r"|\b(?:hold up|stand up) in court\b",
    re.IGNORECASE,
)
SCENARIO_RE = re.compile(
    r"\bwhat (?:if|happens if|happens when|would happen if)\b"
    r"|\bif i (?:leave|resign|quit|move out|vacate|break|end|terminate)\b",
    re.IGNORECASE,
)


@dataclass(frozen=True)
class Route:
    intent: Intent
    reason: str


def route(question: str) -> Route:
    if OUT_OF_SCOPE_RE.search(question):
        return Route(Intent.OUT_OF_SCOPE, "outside the document or an attempt to change instructions")
    if VERDICT_WORDS_RE.search(question) or VERDICT_PATTERNS_RE.search(question):
        return Route(Intent.LEGAL_VERDICT, "asks for a legal conclusion, an outcome or a recommendation")
    if SCENARIO_RE.search(question):
        return Route(Intent.SCENARIO, "a what-if question")
    return Route(Intent.DOCFACT, "a question about what the document says")


SCENARIO_KEYWORDS: dict[str, re.Pattern[str]] = {
    "bond_exit": re.compile(r"\b(?:bond|resign|quit|leave (?:the )?(?:job|company))\b", re.IGNORECASE),
    "deposit_refund": re.compile(r"\b(?:deposit|refund|advance)\b", re.IGNORECASE),
    "rental_early_exit": re.compile(
        r"\b(?:leave|move out|vacate|break the (?:lease|licence|agreement)|end the (?:lease|licence|tenancy))\b",
        re.IGNORECASE,
    ),
}
MONTH_RE = re.compile(
    r"\b(?:month\s+(\d{1,2})|(\d{1,2})\s*(?:st|nd|rd|th)?\s+months?|after\s+(\d{1,2})\s+months?)\b", re.IGNORECASE
)


def scenario_for(question: str, doc_type: str) -> str | None:
    """The scenario a what-if question refers to, if one fits this document type."""
    allowed = {"rental": ["deposit_refund", "rental_early_exit"], "employment": ["bond_exit"]}.get(doc_type, [])
    for scenario_id in allowed:
        if SCENARIO_KEYWORDS[scenario_id].search(question):
            return scenario_id
    return None


def months_in(question: str) -> int | None:
    m = MONTH_RE.search(question)
    if m is None:
        return None
    return int(next(g for g in m.groups() if g))
