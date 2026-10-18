"""What a model may see: clause text with every flagged (excluded) span replaced by a marker.

Hidden instructions are never passed to a prompt. The marker tells the model something was removed without
repeating the removed text.
"""

from __future__ import annotations

from collections.abc import Iterable

from ..models import Clause, HiddenFinding

REMOVED_MARKER = "[flagged text removed]"


def analysis_text(clause: Clause, findings: Iterable[HiddenFinding]) -> str:
    cs, ce = clause.char_start, clause.char_end
    spans = sorted(
        (max(f.char_start, cs) - cs, min(f.char_end, ce) - cs)
        for f in findings
        if f.excluded_from_analysis
        and f.char_start is not None
        and f.char_end is not None
        and f.char_start < ce
        and f.char_end > cs
    )
    out: list[str] = []
    pos = 0
    for start, end in spans:
        if end <= pos:
            continue  # already covered by an earlier span
        out.append(clause.text[pos : max(start, pos)])
        out.append(REMOVED_MARKER)
        pos = end
    out.append(clause.text[pos:])
    return "".join(out)
