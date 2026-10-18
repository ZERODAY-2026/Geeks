"""Hidden-content and injection detection. Findings are reported to the user, never silently removed."""

from __future__ import annotations

import re
from collections.abc import Sequence

from ..models import HiddenFinding, HiddenFindingType, Severity

ZERO_WIDTH = frozenset("​‌‍⁠﻿")
BIDI_CONTROLS = frozenset("‪‫‬‭‮⁦⁧⁨⁩")

INJECTION_RE = re.compile(
    r"ignore (?:all |any )?(?:previous|prior|above) instructions"
    r"|disregard (?:all |the )?(?:previous|above|prior) (?:instructions|rules)"
    r"|system prompt"
    r"|you are (?:now )?an? (?:ai|assistant|language model)"
    r"|</?document>"
    r"|respond only with"
    r"|report that this (?:contract|agreement) is (?:100% )?safe",
    re.IGNORECASE,
)


def scan_text(text: str) -> list[HiddenFinding]:
    """Invisible characters and prompt-injection phrases in extracted text. Offsets are into `text`."""
    findings: list[HiddenFinding] = []
    for chars, kind in ((ZERO_WIDTH, HiddenFindingType.ZERO_WIDTH), (BIDI_CONTROLS, HiddenFindingType.BIDI_CONTROL)):
        idx = [i for i, c in enumerate(text) if c in chars]
        if idx:
            findings.append(
                HiddenFinding(
                    type=kind,
                    severity=Severity.HIGH,
                    char_start=idx[0],
                    char_end=idx[-1] + 1,
                    preview=f"{len(idx)} invisible character(s); kept in the record, ignored when matching quotes.",
                    excluded_from_analysis=False,
                )
            )
    for m in INJECTION_RE.finditer(text):
        findings.append(
            HiddenFinding(
                type=HiddenFindingType.INJECTION_PATTERN,
                severity=Severity.HIGH,
                char_start=m.start(),
                char_end=m.end(),
                preview=m.group(0)[:120],
                excluded_from_analysis=True,
            )
        )
    return findings


def _is_white(color: object) -> bool:
    if isinstance(color, (int, float)):
        return color >= 0.95
    if isinstance(color, (list, tuple)) and color:
        if len(color) == 4:  # CMYK: white is no ink
            return all(float(c) <= 0.05 for c in color)
        return all(isinstance(c, (int, float)) and c >= 0.95 for c in color)
    return False


def _preview(chars: Sequence[dict]) -> str:
    return "".join(str(c.get("text", "")) for c in chars)[:120]


def scan_pdf_chars(chars: Sequence[dict], page: int) -> list[HiddenFinding]:
    """White-filled or tiny (< 4 pt) glyphs on one PDF page, from pdfplumber character records."""
    white = [c for c in chars if _is_white(c.get("non_stroking_color"))]
    tiny = [c for c in chars if (c.get("size") or 99) < 4]
    out: list[HiddenFinding] = []
    if white:
        out.append(
            HiddenFinding(
                type=HiddenFindingType.WHITE_TEXT,
                severity=Severity.HIGH,
                page=page,
                preview=_preview(white),
                excluded_from_analysis=False,
            )
        )
    if tiny:
        out.append(
            HiddenFinding(
                type=HiddenFindingType.TINY_TEXT,
                severity=Severity.HIGH,
                page=page,
                preview=_preview(tiny),
                excluded_from_analysis=False,
            )
        )
    return out
