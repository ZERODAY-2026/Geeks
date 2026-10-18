"""Quote verifier: a model's quote is accepted only if it matches the cited clause, and the returned citation
always carries the SOURCE text at the matched offsets, never the model's version.

Order: exact, then normalized (case, Unicode form, quote styles, dashes, whitespace, hyphenated line breaks,
zero-width characters ignored), then fuzzy (rapidfuzz partial alignment, score >= fuzzy_min). A fuzzy match is
accepted only if its digits and negation words equal the quote's.
"""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass

from rapidfuzz import fuzz

from ..ingest.hidden import ZERO_WIDTH
from ..ingest.segment import line_span, page_of
from ..models import Citation, Clause, MatchType, PageText

MIN_FUZZY_CHARS = 20  # shorter quotes match too easily to trust fuzzily
CURLY = {"‘": "'", "’": "'", "“": '"', "”": '"'}
DASHES = {"–": "-", "—": "-", "‐": "-", "‑": "-", "−": "-"}
NEGATION_RE = re.compile(r"\b(?:not|no|never|without|cannot|nor)\b|n't\b")
DIGITS_RE = re.compile(r"\d+(?:[.,]\d+)*")


@dataclass(frozen=True)
class Normalized:
    text: str
    starts: list[int]  # original index where each normalized character begins
    ends: list[int]  # original index just past each normalized character


def normalize(text: str) -> Normalized:
    """Lowercase, Unicode-normalized, whitespace-collapsed text with a map back to the original offsets."""
    out: list[str] = []
    starts: list[int] = []
    ends: list[int] = []
    i, n = 0, len(text)
    pending_space: int | None = None
    while i < n:
        ch = text[i]
        if ch in ZERO_WIDTH:
            i += 1
            continue
        if ch == "-" and i + 1 < n and text[i + 1] in "\r\n":  # hyphenated line break: join the word
            j = i + 1
            while j < n and text[j] in " \t\r\n":
                j += 1
            i = j
            continue
        if ch.isspace():
            if pending_space is None:
                pending_space = i
            i += 1
            continue
        if pending_space is not None and out:
            out.append(" ")
            starts.append(pending_space)
            ends.append(i)
        pending_space = None
        ch = CURLY.get(ch) or DASHES.get(ch) or ch
        for c in unicodedata.normalize("NFKC", ch).lower():
            out.append(c)
            starts.append(i)
            ends.append(i + 1)
        i += 1
    return Normalized("".join(out), starts, ends)


def _numbers(text: str) -> list[str]:
    return sorted(d.replace(",", "") for d in DIGITS_RE.findall(text))


def negated(text: str) -> bool:
    return bool(NEGATION_RE.search(text.lower()))


def verify_quote(quote: str, clause: Clause, text: str, pages: list[PageText], fuzzy_min: int = 92) -> Citation | None:
    """Return a Citation whose quote is the source text at the matched offsets, or None if nothing matches."""
    if not quote.strip():
        return None
    source = text[clause.char_start : clause.char_end]
    if source != clause.text:  # the offset invariant from segmentation
        raise ValueError(f"clause {clause.id} offsets do not match the document text")

    start = end = None
    match, score = MatchType.EXACT, 100.0
    q = quote.strip()
    idx = clause.text.find(q)
    if idx >= 0:
        start, end = idx, idx + len(q)
    else:
        norm = normalize(clause.text)
        nq = normalize(q).text.strip()
        if nq:
            idx = norm.text.find(nq)
            if idx >= 0:
                start, end = norm.starts[idx], norm.ends[idx + len(nq) - 1]
                match = MatchType.NORMALIZED
            elif len(nq) >= MIN_FUZZY_CHARS:
                al = fuzz.partial_ratio_alignment(nq, norm.text)
                if al is not None and al.score >= fuzzy_min:
                    span = clause.text[norm.starts[al.dest_start] : norm.ends[al.dest_end - 1]]
                    if _numbers(span) == _numbers(q) and negated(span) == negated(q):
                        start, end = norm.starts[al.dest_start], norm.ends[al.dest_end - 1]
                        match, score = MatchType.FUZZY, float(al.score)
    if start is None or end is None or end <= start:
        return None
    g_start = clause.char_start + start
    g_end = clause.char_start + end
    line_start, line_end = line_span(pages, g_start, g_end)
    return Citation(
        page=page_of(pages, g_start),
        char_start=g_start,
        char_end=g_end,
        clause_id=clause.id,
        quote=text[g_start:g_end],  # always the source text
        match=match,
        score=score,
        line_start=line_start,
        line_end=line_end,
    )
