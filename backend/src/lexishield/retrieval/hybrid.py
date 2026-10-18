"""Hybrid retrieval: BM25 and dense rankings fused with reciprocal-rank fusion, plus cross-reference expansion."""

from __future__ import annotations

from collections import defaultdict
from contextlib import suppress

from ..llm.gateway import LLMError, LLMGateway
from .bm25 import bm25_ranking
from .embed import dense_ranking

RRF_K = 60  # standard reciprocal-rank-fusion constant


async def hybrid_top_k(gw: LLMGateway, query: str, ids: list[str], texts: list[str], k: int) -> list[str]:
    """Top-k clause ids for a query. If the model is unavailable, falls back to BM25 alone."""
    rankings = [bm25_ranking(query, texts)]
    with suppress(LLMError):  # BM25 only: a documented fallback, never a guessed embedding
        rankings.append(await dense_ranking(gw, query, texts))
    scores: dict[int, float] = defaultdict(float)
    for ranking in rankings:
        for rank, idx in enumerate(ranking, 1):
            scores[idx] += 1.0 / (RRF_K + rank)
    order = sorted(range(len(texts)), key=lambda i: (-scores[i], i))
    return [ids[i] for i in order[:k]]


def expand_xrefs(top: list[str], xrefs: dict[str, list[str]]) -> list[str]:
    """Clauses that the top hits refer to, not already in `top`, in order of first reference."""
    seen = set(top)
    extra: list[str] = []
    for cid in top:
        for ref in xrefs.get(cid, []):
            if ref not in seen:
                seen.add(ref)
                extra.append(ref)
    return extra
