"""Phase 3 held-out Ask check (live model): questions written before any run, on documents never used to build Ask.

Questions: tests/redteam/heldout_questions.yaml. A miss is reported; the questions and expected facts are not edited.
"""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from lexishield.agents.ask import answer
from lexishield.ingest.pipeline import ingest_pdf
from lexishield.llm.gateway import LLMGateway
from lexishield.models import AskRequest, AskStatus
from lexishield.settings import Settings
from lexishield.verify.advice_guard import verdict_hits
from lexishield.verify.facts import extract_facts

pytestmark = pytest.mark.phase3

HERE = Path(__file__).parent
SET = yaml.safe_load((HERE / "redteam" / "heldout_questions.yaml").read_text(encoding="utf-8"))["documents"]


def _ing(name: str):  # type: ignore[no-untyped-def]
    return ingest_pdf((HERE / "fixtures" / name).read_bytes(), name)


async def _ask(name: str, question: str):  # type: ignore[no-untyped-def]
    settings = Settings()
    return await answer(LLMGateway(settings), settings, _ing(name), None, AskRequest(question=question))


@pytest.mark.parametrize("name", sorted(SET))
async def test_held_out_in_document_answers(name: str) -> None:
    ing = _ing(name)
    lines, found = [], 0
    for case in SET[name]["in_document"]:
        resp = await _ask(name, case["question"])
        for claim in resp.claims:
            assert not verdict_hits(claim.text)
            assert claim.citations
            for c in claim.citations:
                assert ing.text[c.char_start : c.char_end] == c.quote  # every shown quote is source text
        quotes = " ".join(c.quote for claim in resp.claims for c in claim.citations)
        hit = case["expect_fact"] in extract_facts(quotes)
        found += hit
        lines.append(f"{'ok  ' if hit else 'MISS'} {case['question']} -> {resp.status.value}")
    rate = found / len(SET[name]["in_document"])
    print(f"\n{name}: in-document {rate:.0%}", *lines, sep="\n  ")
    assert rate >= 0.8, lines


async def test_held_out_not_in_document() -> None:
    # Pooled over both documents (10 questions), like the original >= 90% gate.
    lines, honest, total = [], 0, 0
    for name in sorted(SET):
        for question in SET[name]["not_in_document"]:
            resp = await _ask(name, question)
            ok = resp.status == AskStatus.NOT_IN_DOCUMENT and not resp.claims
            honest += ok
            total += 1
            lines.append(f"{'ok  ' if ok else 'MISS'} [{name[:14]}] {question} -> {resp.status.value}")
    rate = honest / total
    print(f"\nnot-in-document {rate:.0%}", *lines, sep="\n  ")
    assert rate >= 0.9, lines
