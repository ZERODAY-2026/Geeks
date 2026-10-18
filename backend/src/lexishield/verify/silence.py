"""Silence double-key and status rules.

A topic is reported as silent (NOT_MENTIONED) only when the model says so AND a lexicon search of the whole
document finds nothing. If the lexicon finds something, the status is UNCLEAR. A status that claims the text says
something (ENTAILED or CONTRADICTED) needs at least one verified quote, otherwise it is UNCLEAR.
"""

from __future__ import annotations

import re

from ..models import ChecklistStatus


def lexicon_hits(text: str, lexicon: list[str]) -> list[str]:
    """Lexicon terms found at the start of a word in the text (so 'refund' matches 'refunded')."""
    lowered = text.lower()
    return [term for term in lexicon if re.search(rf"(?<![a-z]){re.escape(term.lower())}", lowered)]


def decide_status(
    model_status: ChecklistStatus, has_verified_quote: bool, hits: list[str]
) -> tuple[ChecklistStatus, str | None]:
    """Return the final status and a note explaining any change from the model's answer."""
    if model_status == ChecklistStatus.UNCLEAR:
        return ChecklistStatus.UNCLEAR, None
    if model_status in (ChecklistStatus.ENTAILED, ChecklistStatus.CONTRADICTED) and not has_verified_quote:
        return ChecklistStatus.UNCLEAR, "The model's answer had no quote that matches the document."
    if model_status == ChecklistStatus.NOT_MENTIONED and hits:
        return ChecklistStatus.UNCLEAR, f"Related wording exists ({', '.join(hits[:3])}) but no clear answer."
    return model_status, None
