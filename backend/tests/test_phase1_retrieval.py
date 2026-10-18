"""Phase 1 gate (retrieval): recall@6 on the hand-labelled queries, BM25 fallback, cross-reference expansion."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from conftest import FakeOllama
from lexishield.ingest.pipeline import Ingested, ingest_pdf, ingest_text
from lexishield.ingest.prompt_view import analysis_text
from lexishield.llm.gateway import LLMGateway
from lexishield.retrieval.hybrid import expand_xrefs, hybrid_top_k
from lexishield.settings import Settings

pytestmark = pytest.mark.phase1

FIXTURES = Path(__file__).parent / "fixtures"
KEYS = json.loads((FIXTURES / "answer_keys.json").read_text(encoding="utf-8"))


def _ingest(name: str) -> Ingested:
    data = (FIXTURES / name).read_bytes()
    if name.endswith(".pdf"):
        return ingest_pdf(data, name)
    return ingest_text(data.decode("utf-8"), name)


def _view(ing: Ingested) -> tuple[list[str], list[str]]:
    ids = [c.id for c in ing.clauses]
    texts = [analysis_text(c, ing.hidden) for c in ing.clauses]
    return ids, texts


def _gold_ids(ing: Ingested, numbers: list[str]) -> set[str]:
    by_number = {c.number: c.id for c in ing.clauses if c.number}
    return {by_number[n] for n in numbers}


async def test_recall_at_six_on_labelled_queries() -> None:
    gw = LLMGateway(Settings())  # the real embedding model, through the gateway
    scores = []
    for q in KEYS["retrieval"]:
        ing = _ingest(q["file"])
        ids, texts = _view(ing)
        top = set(await hybrid_top_k(gw, q["query"], ids, texts, k=6))
        gold = _gold_ids(ing, q["gold"])
        scores.append(len(top & gold) / len(gold))
    recall = sum(scores) / len(scores)
    assert len(scores) == 15
    assert recall >= 0.9, f"recall@6 = {recall:.2f}; per query {[round(s, 2) for s in scores]}"


async def test_bm25_fallback_when_the_model_is_down() -> None:
    gw = LLMGateway(Settings(), client=FakeOllama(down=True))
    ing = _ingest("in_rental_11m_leave_license.txt")
    ids, texts = _view(ing)
    top = await hybrid_top_k(gw, "security deposit refund", ids, texts, k=6)
    assert _gold_ids(ing, ["3"]) <= set(top)


def test_cross_reference_expansion_adds_the_referenced_clause() -> None:
    ing = _ingest("in_rental_11m_leave_license.txt")
    xrefs = {c.id: c.xrefs for c in ing.clauses}
    lock_in = next(c.id for c in ing.clauses if c.number == "4")
    termination = next(c.id for c in ing.clauses if c.number == "9")
    assert expand_xrefs([lock_in], xrefs) == [termination]
    assert expand_xrefs([termination], xrefs) == []
