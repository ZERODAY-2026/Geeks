"""Dense retrieval with EmbeddingGemma through the gateway (the only model client)."""

from __future__ import annotations

import numpy as np

from ..llm.gateway import LLMGateway

# EmbeddingGemma's documented prompt formats for search (model card).
QUERY_PREFIX = "task: search result | query: "
DOC_PREFIX = "title: none | text: "


async def dense_ranking(gw: LLMGateway, query: str, docs: list[str]) -> list[int]:
    """Document indices by cosine similarity to the query, best first."""
    if not docs:
        return []
    vectors = np.asarray(await gw.embed([QUERY_PREFIX + query] + [DOC_PREFIX + d for d in docs]), dtype=np.float64)
    q, d = vectors[0], vectors[1:]
    sims = d @ q / (np.linalg.norm(d, axis=1) * np.linalg.norm(q) + 1e-12)
    return sorted(range(len(docs)), key=lambda i: (-sims[i], i))
