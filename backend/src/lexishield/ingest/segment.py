"""Clause segmentation. Every clause keeps exact character offsets into the ORIGINAL text.

Invariant (tested): text[clause.char_start:clause.char_end] == clause.text
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from ..models import Clause, PageText

HEADING_RE = re.compile(r"^[ \t]*(\d{1,2}(?:\.\d{1,2}){0,2})\.?[ \t]+(?=\S)", re.MULTILINE)
PARAGRAPH_SPLIT_RE = re.compile(r"\n[ \t]*\n")
TITLE_RE = re.compile(r"([A-Z][A-Z0-9 &/,'\-]{2,60}?)\.(?=\s|$)")
TERM_RE = re.compile(r'"([A-Z][A-Za-z ]{1,40}?)"')
XREF_RE = re.compile(r"\b[Cc]lause\s+(\d{1,2}(?:\.\d{1,2})?)\b")


@dataclass(frozen=True)
class Span:
    number: str | None
    text: str
    char_start: int
    char_end: int


def _trimmed(text: str, start: int, end: int, number: str | None) -> Span | None:
    raw = text[start:end]
    body = raw.strip()
    if not body:
        return None
    lead = len(raw) - len(raw.lstrip())
    return Span(number=number, text=body, char_start=start + lead, char_end=start + lead + len(body))


def segment(text: str) -> list[Span]:
    heads = list(HEADING_RE.finditer(text))
    blocks: list[tuple[int, int, str | None]] = []
    if not heads:
        pos = 0
        for m in PARAGRAPH_SPLIT_RE.finditer(text):
            blocks.append((pos, m.start(), None))
            pos = m.end()
        blocks.append((pos, len(text), None))
    else:
        if heads[0].start() > 0:
            blocks.append((0, heads[0].start(), None))  # preamble before the first numbered clause
        for i, m in enumerate(heads):
            end = heads[i + 1].start() if i + 1 < len(heads) else len(text)
            blocks.append((m.start(), end, m.group(1)))
    spans = [_trimmed(text, s, e, n) for s, e, n in blocks]
    return [s for s in spans if s is not None]


def _heading(body: str, number: str | None) -> str | None:
    if number is None:
        return None
    m = TITLE_RE.match(body[len(number) :].lstrip(" .\t"))
    return m.group(1).strip() if m else None


def page_of(pages: list[PageText], offset: int) -> int:
    for p in pages:
        if p.char_start <= offset < p.char_end:
            return p.page
    return pages[-1].page


def line_span(pages: list[PageText], char_start: int, char_end: int) -> tuple[int, int]:
    """1-based lines, within the page where the span starts, of the first and last character of [char_start, char_end).

    A span that runs onto the next page ends at that page's last line, so both numbers refer to the same page.
    """
    page = next((p for p in pages if p.char_start <= char_start < p.char_end), pages[-1])
    rel_start = max(0, char_start - page.char_start)
    rel_last = min(len(page.text), max(rel_start + 1, char_end - page.char_start)) - 1
    return page.text.count("\n", 0, rel_start) + 1, page.text.count("\n", 0, rel_last) + 1


def build_clauses(text: str, pages: list[PageText]) -> list[Clause]:
    spans = segment(text)
    id_by_number = {s.number: f"C{i}" for i, s in enumerate(spans, 1) if s.number}
    clauses: list[Clause] = []
    for i, s in enumerate(spans, 1):
        cid = f"C{i}"
        xrefs = sorted({id_by_number[n] for n in XREF_RE.findall(s.text) if n in id_by_number} - {cid})
        clauses.append(
            Clause(
                id=cid,
                number=s.number,
                heading=_heading(s.text, s.number),
                text=s.text,
                page_start=page_of(pages, s.char_start),
                page_end=page_of(pages, max(s.char_start, s.char_end - 1)),
                char_start=s.char_start,
                char_end=s.char_end,
                defined_terms=sorted(set(TERM_RE.findall(s.text))),
                xrefs=xrefs,
            )
        )
    return clauses
