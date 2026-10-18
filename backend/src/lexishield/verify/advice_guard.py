"""Advice guard: blocks verdict language about legality, validity or outcome.

LexiShield never says a clause is enforceable, illegal, void, fair or a reason to sign. A hit withholds the text
it was found in. The list is deliberately conservative: a false hit only withholds a sentence, a miss would
give advice.
"""

from __future__ import annotations

import re

VERDICT_RE = re.compile(
    r"\b(?:is|are|be)\s+(?:un)?enforceable\b"
    r"|\b(?:is|are)\s+(?:il)?legal\b(?!\s+notice)"
    r"|\b(?:is|are)\s+(?:in)?valid\b"
    r"|\bvoid\b"
    r"|\byou should (?:sign|accept|reject|refuse)\b"
    r"|\byou will (?:win|lose)\b"
    r"|\bdefinitely\b"
    r"|\bguarantee[ds]?\b"
    r"|\b(?:is|are) (?:un)?fair\b",
    re.IGNORECASE,
)

WITHHELD_REASON = "The explanation contained a verdict about legality or outcome, so it was withheld."


def verdict_hits(text: str) -> list[str]:
    return [m.group(0) for m in VERDICT_RE.finditer(text)]
