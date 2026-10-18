"""Clause card writer: plain-language explanation with stated facts, interpretations, ambiguity and questions.

A card shows the explanation only when the distortion checker and the advice guard both let it through.
Otherwise it shows the verified source quote and the reason the explanation was withheld.
"""

from __future__ import annotations

import nltk
import textstat
from pydantic import BaseModel, Field

from ..models import (
    ChecklistStatus,
    Citation,
    Claim,
    ClaimKind,
    ClauseCard,
    Country,
    Distortion,
    Severity,
    Tier,
)
from ..settings import BACKEND_DIR
from ..verify.advice_guard import WITHHELD_REASON, verdict_hits
from ..verify.facts import extract_facts

DISTORTION_WITHHELD = "We couldn't verify this explanation against the clause. Read the clause, or ask a professional."
NO_SOURCE_REASON = "No clause in the document supports this explanation, so it is not shown."
JURISDICTION_NOTE = "Rules differ by state or country and are checked against local law. Check with a professional."
FOREIGN_NOTE = "This document appears to follow {country} law. The checklist is written for India, so check locally."


class CardInput(BaseModel):
    """What the checklist agent passes to the card writer for one topic."""

    topic_id: str
    title: str
    severity: Severity
    status: ChecklistStatus
    tier: Tier
    explanation: str = Field(default="")
    distortion: Distortion
    distortion_reasons: list[str] = Field(default_factory=list)
    citations: list[Citation] = Field(default_factory=list)
    stated: list[str] = Field(default_factory=list)
    interpretations: list[str] = Field(default_factory=list)
    ambiguity: list[str] = Field(default_factory=list)
    questions: list[str] = Field(default_factory=list)
    jurisdiction_sensitive: bool = False
    jurisdiction_dependent: bool = False
    country: Country = Country.IN


# textstat counts syllables with NLTK's cmudict and downloads it on first use if it is missing. This app runs
# offline, so the data is installed once at set-up time (scripts/prepare_offline.py) into backend/data/nltk_data,
# and the grade is only measured when that data is present. A missing grade is better than a network call.
LOCAL_NLTK_DATA = BACKEND_DIR / "data" / "nltk_data"
if LOCAL_NLTK_DATA.exists():
    nltk.data.path.insert(0, str(LOCAL_NLTK_DATA))


def syllable_data_installed() -> bool:
    try:
        nltk.data.find("corpora/cmudict")
    except LookupError:
        return False
    return True


def reading_grade(text: str) -> float | None:
    if not text.strip() or not syllable_data_installed():
        return None
    return round(float(textstat.flesch_kincaid_grade(text)), 1)


def _clean(items: list[str]) -> list[str]:
    return [s for s in items if s.strip() and not verdict_hits(s)]


def build_card(inp: CardInput) -> ClauseCard:
    withheld: str | None = None
    explanation = inp.explanation
    if explanation and verdict_hits(explanation):
        withheld = WITHHELD_REASON
    elif explanation and not inp.citations:
        withheld = NO_SOURCE_REASON  # nothing reaches the user without a verified source span
    elif inp.distortion == Distortion.FAIL:
        withheld = DISTORTION_WITHHELD
    show = bool(explanation) and withheld is None

    plain = None
    if show:
        kind = (
            ClaimKind.STATED
            if inp.status in (ChecklistStatus.ENTAILED, ChecklistStatus.CONTRADICTED)
            else (ClaimKind.INTERPRETATION)
        )
        plain = Claim(
            text=explanation,
            kind=kind,
            citations=inp.citations,
            distortion=inp.distortion,
            facts=sorted(extract_facts(explanation)),
        )

    flags: list[str] = []
    if inp.jurisdiction_sensitive or inp.jurisdiction_dependent:
        flags.append(JURISDICTION_NOTE)
    if inp.country not in (Country.IN, Country.UNKNOWN):
        flags.append(FOREIGN_NOTE.format(country=inp.country.value))

    return ClauseCard(
        id=f"card_{inp.topic_id}",
        topic_id=inp.topic_id,
        title=inp.title,
        severity=inp.severity,
        tier=inp.tier,
        reading_grade=reading_grade(explanation) if show else None,
        source=inp.citations[0] if inp.citations else None,
        plain_explanation=plain,
        explanation_withheld_reason=withheld,
        stated=_clean(inp.stated) if show else [],
        interpretations=[
            Claim(text=t, kind=ClaimKind.INTERPRETATION, citations=inp.citations, distortion=Distortion.NA)
            for t in _clean(inp.interpretations)
        ]
        if show
        else [],
        ambiguity_flags=_clean(inp.ambiguity),
        jurisdiction_flags=flags,
        questions_for_lawyer=_clean(inp.questions),
    )
