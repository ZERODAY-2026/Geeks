"""Lexical retrieval: BM25 over clause text."""

from __future__ import annotations

import re

from rank_bm25 import BM25Okapi

TOKEN_RE = re.compile(r"[a-z0-9]+")
STOPWORDS = frozenset(
    [
        "a",
        "an",
        "and",
        "are",
        "as",
        "at",
        "be",
        "by",
        "for",
        "from",
        "has",
        "have",
        "if",
        "in",
        "is",
        "it",
        "its",
        "of",
        "on",
        "or",
        "shall",
        "that",
        "the",
        "their",
        "this",
        "to",
        "under",
        "with",
        "will",
        "would",
        "any",
        "each",
        "may",
        "must",
    ]
)


def tokenize(text: str) -> list[str]:
    return [t for t in TOKEN_RE.findall(text.lower()) if t not in STOPWORDS]


def bm25_ranking(query: str, docs: list[str]) -> list[int]:
    """Document indices, best first. Ties keep document order."""
    if not docs:
        return []
    scores = BM25Okapi([tokenize(d) or ["_"] for d in docs]).get_scores(tokenize(query) or ["_"])
    return sorted(range(len(docs)), key=lambda i: (-scores[i], i))
