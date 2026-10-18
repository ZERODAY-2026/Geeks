"""Phase 2 third fresh held-out check (live model): new documents, keys written before any run, three runs each.

Keys: tests/fixtures/fresh3_keys.json. Documents: made by scripts/make_fresh_fixtures.py. Model output varies between
runs, so each document is analysed RUNS times and the spread is reported, not only the best run. Every run must reach
80% of its topics. A miss is reported; the key is not edited.
"""

from __future__ import annotations

import json
import statistics
from pathlib import Path

import pytest

from lexishield.agents.orchestrator import run_analysis
from lexishield.ingest.pipeline import ingest_pdf
from lexishield.llm.gateway import LLMGateway
from lexishield.models import AnalyzeRequest, ChecklistStatus
from lexishield.settings import Settings

pytestmark = pytest.mark.phase2

RUNS = 3
FIXTURES = Path(__file__).parent / "fixtures"
KEYS = json.loads((FIXTURES / "fresh3_keys.json").read_text(encoding="utf-8"))
SILENT_OK = {ChecklistStatus.NOT_MENTIONED, ChecklistStatus.UNCLEAR}
_CACHE: dict[tuple[str, int], object] = {}


async def _run(name: str):  # type: ignore[no-untyped-def]
    settings = Settings()
    gw = LLMGateway(settings)

    async def emit(n: str, data: dict) -> None:
        return None

    ing = ingest_pdf((FIXTURES / name).read_bytes(), name)
    return await run_analysis(gw, settings, ing, "doc_fresh3", AnalyzeRequest(), emit, lambda: False)


async def _report(name: str, run: int):  # type: ignore[no-untyped-def]
    if (name, run) not in _CACHE:
        _CACHE[(name, run)] = await _run(name)
    return _CACHE[(name, run)]


def _score(expected: dict[str, str], report) -> tuple[int, int, list[str]]:  # type: ignore[no-untyped-def]
    got = {i.topic_id: i.status for i in report.checklist}
    correct, misses = 0, []
    for topic_id, want in expected.items():
        status = got.get(topic_id)
        ok = status in SILENT_OK if want == "SILENT" else status == ChecklistStatus(want)
        correct += ok
        if not ok:
            misses.append(f"{topic_id}: expected {want}, got {status}")
    return correct, len(expected), misses


@pytest.mark.parametrize("name", sorted(KEYS["documents"]))
async def test_fresh_document_meets_the_gate_on_every_run(name: str) -> None:
    expected = KEYS["documents"][name]["topics"]
    rates: list[float] = []
    lines: list[str] = []
    for run in range(1, RUNS + 1):
        report = await _report(name, run)
        assert report.pack_id == KEYS["documents"][name]["pack"]
        correct, total, misses = _score(expected, report)
        rates.append(correct / total)
        lines.append(f"run {run}: {correct}/{total} ({correct / total:.0%})")
        lines += [f"    {m}" for m in misses]
    print(f"\n{name}\n  " + "\n  ".join(lines))
    print(f"  mean {statistics.mean(rates):.0%}, range {min(rates):.0%} to {max(rates):.0%}")
    assert min(rates) >= 0.8, "\n".join(lines)


async def test_fresh_silences_are_never_entailed() -> None:
    for name in KEYS["documents"]:
        report = await _report(name, 1)
        got = {i.topic_id: i.status for i in report.checklist}
        for topic_id, want in KEYS["documents"][name]["topics"].items():
            if want == "SILENT":
                assert got.get(topic_id) in SILENT_OK, f"{name} {topic_id}: {got.get(topic_id)}"


async def test_fresh_citations_are_verified_source_text() -> None:
    for name in KEYS["documents"]:
        report = await _report(name, 1)
        doc = ingest_pdf((FIXTURES / name).read_bytes(), name)
        for item in report.checklist:
            for c in item.evidence:
                assert doc.text[c.char_start : c.char_end] == c.quote, name
        assert report.metrics.unverified_displayed == 0
