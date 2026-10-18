"""Ingestion pipeline: bytes or text in, pages + clauses + findings out. Nothing leaves the process.

Text used for clauses, offsets and prompts is the VISIBLE text only. Hidden glyphs (white or tiny PDF text,
white or hidden DOCX runs) never reach the clause tree; they are reported as findings so the user can see them.
"""

from __future__ import annotations

import io
from dataclasses import dataclass, field

from ..models import Clause, HiddenFinding, HiddenFindingType, IngestionWarning, PageText, QuickDetect, Severity
from .hidden import is_hidden_glyph, scan_pdf_chars, scan_text
from .quick import quick_detect
from .segment import build_clauses, page_of

PAGE_SEPARATOR = "\n\n"


class IngestError(Exception):
    def __init__(self, status: int, code: str, title: str, detail: str) -> None:
        super().__init__(detail)
        self.status, self.code, self.title, self.detail = status, code, title, detail


@dataclass
class Ingested:
    text: str
    pages: list[PageText]
    clauses: list[Clause]
    hidden: list[HiddenFinding] = field(default_factory=list)
    warnings: list[IngestionWarning] = field(default_factory=list)
    quick: QuickDetect = field(default_factory=QuickDetect)
    scanned: bool = False


def _finish(text: str, pages: list[PageText], hidden: list[HiddenFinding]) -> Ingested:
    visible = scan_text(text)
    # An injection phrase found only in hidden text is reported once, without offsets (it is not in `text`).
    seen = {f.preview for f in visible if f.type == HiddenFindingType.INJECTION_PATTERN}
    hidden = [
        h
        for h in hidden
        if not (h.type == HiddenFindingType.INJECTION_PATTERN and h.char_start is None and h.preview in seen)
    ]
    findings = hidden + visible
    findings = [
        f.model_copy(update={"page": page_of(pages, f.char_start)}) if f.char_start is not None else f for f in findings
    ]
    warnings = []
    if findings:
        warnings.append(
            IngestionWarning(
                code="HIDDEN_CONTENT_FOUND",
                severity=Severity.HIGH,
                message=f"{len(findings)} hidden or invisible finding(s). Shown to you; do not trust that text.",
            )
        )
    return Ingested(
        text=text,
        pages=pages,
        clauses=build_clauses(text, pages),
        hidden=findings,
        warnings=warnings,
        quick=quick_detect(text),
    )


def _empty_check(text: str) -> None:
    if not text.strip():
        raise IngestError(422, "EMPTY_DOCUMENT", "Empty document", "The text is empty after trimming whitespace.")


def ingest_text(text: str, filename: str = "pasted.txt") -> Ingested:  # noqa: ARG001 (kept for symmetry)
    _empty_check(text)
    pages = [PageText(page=1, text=text, char_start=0, char_end=len(text))]
    return _finish(text, pages, hidden=[])


def _chain(exc: BaseException) -> list[BaseException]:
    """The exception and everything it wraps. pdfplumber wraps pdfminer's errors in PdfminerException."""
    out: list[BaseException] = []
    cur: BaseException | None = exc
    while cur is not None and cur not in out:
        out.append(cur)
        nxt = cur.__cause__ or (cur.args[0] if cur.args and isinstance(cur.args[0], BaseException) else None)
        cur = nxt
    return out


def _pdf_error(exc: Exception) -> IngestError:
    names = " ".join(type(e).__name__ + " " + str(e) for e in _chain(exc)).lower()
    if "password" in names or "encrypt" in names:
        return IngestError(
            422,
            "ENCRYPTED_PDF",
            "Encrypted PDF",
            "This PDF is password-protected. Remove the password and upload again.",
        )
    return IngestError(422, "MALFORMED_FILE", "Malformed file", "This file could not be read as a PDF.")


def ingest_pdf(data: bytes, filename: str = "upload.pdf") -> Ingested:  # noqa: ARG001
    import pdfplumber

    try:
        pdf = pdfplumber.open(io.BytesIO(data))
    except Exception as e:  # pdfminer raises several types for bad or encrypted input
        raise _pdf_error(e) from e
    texts: list[str] = []
    hidden: list[HiddenFinding] = []
    try:
        with pdf:
            for number, page in enumerate(pdf.pages, 1):
                hidden.extend(scan_pdf_chars(page.chars, number))
                visible = page.filter(lambda o: o.get("object_type") != "char" or not is_hidden_glyph(o))
                texts.append(visible.extract_text() or "")
                hidden_text = page.filter(lambda o: o.get("object_type") == "char" and is_hidden_glyph(o))
                # Injection phrases in hidden glyphs are reported (no offsets: they are not in the clause text).
                for f in scan_text(hidden_text.extract_text() or ""):
                    if f.type == HiddenFindingType.INJECTION_PATTERN:
                        hidden.append(f.model_copy(update={"page": number, "char_start": None, "char_end": None}))
    except Exception as e:
        raise _pdf_error(e) from e

    pages: list[PageText] = []
    pos = 0
    for number, t in enumerate(texts, 1):
        pages.append(PageText(page=number, text=t, char_start=pos, char_end=pos + len(t)))
        pos += len(t) + len(PAGE_SEPARATOR)
    text = PAGE_SEPARATOR.join(texts)
    if not text.strip():
        raise IngestError(
            422,
            "SCANNED_NO_TEXT",
            "No text layer found",
            "This PDF has no text layer. Scanned documents need local OCR, which is not enabled yet.",
        )
    return _finish(text, pages, hidden=hidden)


def ingest_docx(data: bytes, filename: str = "upload.docx") -> Ingested:  # noqa: ARG001
    import docx
    from docx.shared import RGBColor

    try:
        document = docx.Document(io.BytesIO(data))
    except Exception as e:  # python-docx raises several types for bad input
        raise IngestError(422, "MALFORMED_FILE", "Malformed file", "This file could not be read as a DOCX.") from e

    lines: list[str] = []
    hidden: list[HiddenFinding] = []
    for para in document.paragraphs:
        shown = []
        for run in para.runs:
            color = run.font.color.rgb if run.font.color is not None else None
            is_white = color == RGBColor(0xFF, 0xFF, 0xFF)
            if run.font.hidden or is_white:
                # DOCX has no 'tiny' type; hidden (vanish) runs are reported as TINY_TEXT, the closest type.
                hidden.append(
                    HiddenFinding(
                        type=HiddenFindingType.WHITE_TEXT if is_white else HiddenFindingType.TINY_TEXT,
                        severity=Severity.HIGH,
                        page=1,
                        preview=run.text[:120],
                        excluded_from_analysis=False,
                    )
                )
            else:
                shown.append(run.text)
        lines.append("".join(shown))
    text = "\n".join(lines)
    _empty_check(text)
    pages = [PageText(page=1, text=text, char_start=0, char_end=len(text))]
    return _finish(text, pages, hidden=hidden)
