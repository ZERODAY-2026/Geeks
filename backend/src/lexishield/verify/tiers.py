"""Confidence tiers shown on every card.

STATED           the text says it, a verified quote supports it, and the explanation checks out.
INTERPRETATION   the text supports it, but the explanation has a warning (wording or party may differ).
NOT_FOUND        the document is silent on the topic (double-key checked).
ASK_A_LAWYER     the text is unclear, nothing verified supports the answer, or the explanation was withheld.
"""

from __future__ import annotations

from ..models import ChecklistStatus, Citation, Distortion, Tier


def tier(status: ChecklistStatus, citations: list[Citation], distortion: Distortion) -> Tier:
    if status == ChecklistStatus.NOT_MENTIONED:
        return Tier.NOT_FOUND
    if status == ChecklistStatus.UNCLEAR or not citations or distortion == Distortion.FAIL:
        return Tier.ASK_A_LAWYER
    if distortion == Distortion.WARN:
        return Tier.INTERPRETATION
    return Tier.STATED
