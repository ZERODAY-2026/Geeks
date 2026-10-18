"""Ingestion pipeline: bytes or text in, pages + clauses + findings out. Nothing leaves the process."""

from __future__ import annotations

import io
from dataclasses import dataclass, field

from ..models import Clause, HiddenFinding, IngestionWarning, PageText, QuickDetect, Severity
from .hidden import scan_pdf_chars, scan_text
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
    findings = hidden + scan_text(text)
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


def ingest_text(text: str, filename: str = "pasted.txt") -> Ingested:  # noqa: ARG001 (kept for symmetry)
    if not text.strip():
        raise IngestError(422, "EMPTY_DOCUMENT", "Empty document", "The text is empty after trimming whitespace.")
    pages = [PageText(page=1, text=text, char_start=0, char_end=len(text))]
    return _finish(text, pages, hidden=[])


def _pdf_error(exc: Exception) -> IngestError:
    if "password" in type(exc).__name__.lower() or "encrypt" in str(exc).lower():
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
                texts.append(page.extract_text() or "")
                hidden.extend(scan_pdf_chars(page.chars, number))
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
