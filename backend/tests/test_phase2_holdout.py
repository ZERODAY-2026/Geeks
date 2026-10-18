"""Phase 2 held-out check (live model): documents the prompts were never tuned on, scored against keys written first.

Keys: tests/fixtures/holdout_keys.json. Documents: in_rental_holdout_flat.pdf and in_employment_holdout_offer.pdf
(made by scripts/make_holdout_fixtures.py) and msa_freelance_generic.pdf and legal_notice_demand.pdf (the MSA and
notice fixtures were not used for prompt tuning; the golden test ran only the rental and offer documents).

Each document must reach at least 80% of its topics. A miss is reported, not fixed by editing the key.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from lexishield.agents.orchestrator import run_analysis
from lexishield.ingest.pipeline import ingest_pdf
from lexishield.llm.gateway import LLMGateway
from lexishield.models import AnalyzeRequest, ChecklistStatus
from lexishield.settings import Settings

pytestmark = pytest.mark.phase2

FIXTURES = Path(__file__).parent / "fixtures"
KEYS = json.loads((FIXTURES / "holdout_keys.json").read_text(encoding="utf-8"))
SILENT_OK = {ChecklistStatus.NOT_MENTIONED, ChecklistStatus.UNCLEAR}
_CACHE: dict = {}


async def _run(name: str):  # type: ignore[no-untyped-def]
    settings = Settings()
    gw = LLMGateway(settings)
    events: list[tuple[str, dict]] = []

    async def emit(n: str, data: dict) -> None:
        events.append((n, data))

    ing = ingest_pdf((FIXTURES / name).read_bytes(), name)
    report = await run_analysis(gw, settings, ing, "doc_holdout", AnalyzeRequest(), emit, lambda: False)
    return report, events


async def _results() -> dict:
    if not _CACHE:
        for name in KEYS["documents"]:
            _CACHE[name] = await _run(name)
    return _CACHE


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
async def test_held_out_accuracy_meets_the_gate(name: str) -> None:
    report, _ = (await _results())[name]
    expected = KEYS["documents"][name]["topics"]
    assert report.pack_id == KEYS["documents"][name]["pack"]
    correct, total, misses = _score(expected, report)
    print(f"\n{name}: {correct}/{total} ({correct / total:.0%})", *misses, sep="\n  ")
    assert correct / total >= 0.8, "\n".join(misses)


async def test_no_silence_is_ever_entailed() -> None:
    for name, (report, _) in (await _results()).items():
        got = {i.topic_id: i.status for i in report.checklist}
        for topic_id, want in KEYS["documents"][name]["topics"].items():
            if want == "SILENT":
                assert got.get(topic_id) in SILENT_OK, f"{name} {topic_id}: {got.get(topic_id)}"


async def test_every_displayed_citation_is_verified_source_text() -> None:
    for name, (report, _) in (await _results()).items():
        doc = ingest_pdf((FIXTURES / name).read_bytes(), name)
        for item in report.checklist:
            for c in item.evidence:
                assert doc.text[c.char_start : c.char_end] == c.quote, name
        assert report.metrics.unverified_displayed == 0
