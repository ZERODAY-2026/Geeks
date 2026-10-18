"""Deterministic first-pass document type and jurisdiction signals. Gemma confirms these in Phase 2."""

from __future__ import annotations

import re

from ..models import Country, DocType, QuickDetect

DOC_SIGNALS: dict[DocType, list[str]] = {
    DocType.RENTAL: [
        r"\blicensor\b",
        r"\blicensee\b",
        r"\blandlord\b",
        r"\btenant\b",
        r"\blessor\b",
        r"\blessee\b",
        r"leave and licen",
        r"security deposit",
        r"\bpremises\b",
    ],
    DocType.EMPLOYMENT: [
        r"\bemployee\b",
        r"\bemployer\b",
        r"offer letter",
        r"probation",
        r"\bdesignation\b",
        r"\bctc\b",
        r"notice period",
        r"service bond",
    ],
    DocType.MSA: [
        r"freelanc",
        r"\bcontractor\b",
        r"statement of work",
        r"deliverables",
        r"\bmilestone",
        r"\binvoice",
        r"kill fee",
        r"indemnif",
    ],
    DocType.LEGAL_NOTICE: [
        r"legal notice",
        r"hereby call upon",
        r"\bdemand\b",
        r"without prejudice",
        r"legal proceedings",
        r"within (?:fifteen|thirty|\d+) (?:calendar )?days",
    ],
}

COUNTRY_SIGNALS: dict[Country, list[str]] = {
    Country.IN: [
        r"\brs\.",
        r"₹",
        r"\brupees?\b",
        r"\binr\b",
        r"\blakh\b",
        r"\bbengaluru\b",
        r"\bkarnataka\b",
        r"\bmaharashtra\b",
        r"\bdelhi\b",
        r"\bpune\b",
        r"\bmumbai\b",
        r"\bindia\b",
        r"stamp duty",
    ],
    Country.UK: [r"england and wales", r"\bsolicitor\b", r"\bpounds? sterling\b"],
    Country.US: [r"governed by the laws of the state of", r"\bu\.s\.\b", r"\$\d"],
}


def _best(text: str, signals: dict) -> tuple:
    scores = {k: sum(len(re.findall(p, text, re.IGNORECASE)) for p in pats) for k, pats in signals.items()}
    return max(scores.items(), key=lambda kv: kv[1])


def quick_detect(text: str) -> QuickDetect:
    doc, doc_score = _best(text, DOC_SIGNALS)
    country, c_score = _best(text, COUNTRY_SIGNALS)
    return QuickDetect(
        doc_type=doc if doc_score >= 2 else DocType.UNKNOWN,
        country=country if c_score >= 1 else Country.UNKNOWN,
    )


GOVERNING_LAW_RE = re.compile(
    r"governed by (?:the )?laws? of (India|England and Wales|the State of [A-Z][A-Za-z]+(?: [A-Z][A-Za-z]+)*)"
)


def governing_law(text: str) -> tuple[Country, int, int] | None:
    """The governing-law sentence phrase and the country it names. Offsets are into `text`."""
    m = GOVERNING_LAW_RE.search(text)
    if m is None:
        return None
    named = m.group(1)
    if named == "India":
        country = Country.IN
    elif named == "England and Wales":
        country = Country.UK
    else:
        country = Country.US
    return country, m.start(), m.end()
