"""Distortion checker: does a plain-language explanation say what the cited source says?

Rule 1 (FAIL): every fact in the explanation (amount, duration, percentage, date) must appear in the cited text.
Rule 2 (WARN): negation polarity must match: 'shall not' in the source and a plain 'must' in the explanation differ.
Rule 3 (WARN): the party who is obliged in the source must be the party the explanation names.

Rules 2 and 3 are heuristics that catch common misreadings; they do not prove an explanation is right.
"""

from __future__ import annotations

import re

from ..models import Citation, Distortion
from .facts import extract_facts

# Party words in a clause and the role they stand for. Explanations use the same words.
ROLE_TERMS = {
    "tenant": "tenant", "licensee": "tenant", "lessee": "tenant",
    "landlord": "landlord", "licensor": "landlord", "lessor": "landlord",
    "employee": "employee", "employer": "employer",
    "contractor": "contractor", "freelancer": "contractor", "client": "client",
    "recipient": "recipient", "sender": "sender",
}  # fmt: skip
OBLIGATION_RE = re.compile(r"\b(" + "|".join(ROLE_TERMS) + r")\s+(?:shall|must|will)\b", re.IGNORECASE)


# Only modal negations ('shall not', 'must not', 'without') flip an obligation. 'No interest' or 'interest-free' do not.
MODAL_NEGATION_RE = re.compile(
    r"\b(?:shall|must|may|will|can|should|cannot)\s+not\b|\bcannot\b|\bwithout\b|\bnever\b", re.IGNORECASE
)


def modal_negated(text: str) -> bool:
    return bool(MODAL_NEGATION_RE.search(text))


def _roles_in(text: str) -> set[str]:
    return {ROLE_TERMS[w] for w in ROLE_TERMS if re.search(rf"\b{w}\b", text, re.IGNORECASE)}


def _obligated_roles(source: str, party_roles: dict[str, object]) -> set[str]:
    roles = {ROLE_TERMS[m.group(1).lower()] for m in OBLIGATION_RE.finditer(source)}
    for party, role in party_roles.items():
        if re.search(rf"{re.escape(party)}\s+(?:shall|must|will)\b", source):
            roles.add(str(role))
    return roles


def check(explanation: str, citations: list[Citation], party_roles: dict[str, object]) -> tuple[Distortion, list[str]]:
    """Return the distortion result and the reasons for it."""
    if not explanation.strip() or not citations:
        return Distortion.NA, []
    source = " ".join(c.quote for c in citations)
    src_facts = set().union(*(extract_facts(c.quote) for c in citations))
    missing = sorted(extract_facts(explanation) - src_facts)
    if missing:
        return Distortion.FAIL, [f"explanation states {', '.join(missing)}, which the cited text does not"]
    warnings: list[str] = []
    if modal_negated(explanation) != modal_negated(source):
        warnings.append("negation differs between the explanation and the cited text")
    obligated = _obligated_roles(source, party_roles)
    named = _roles_in(explanation)
    if obligated and named and not (obligated & named):
        warnings.append("the explanation names a different party as the one obliged")
    if warnings:
        return Distortion.WARN, warnings
    return Distortion.PASS, []
