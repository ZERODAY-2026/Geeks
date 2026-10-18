"""Phase 2 gate (golden documents, live Gemma): topic statuses against the answer key, silence recall, reading grade.

Needs Ollama running with the configured models. Answer keys are in tests/fixtures/golden_keys.json and were written
before the first run. Thresholds are the plan's gate; a miss is a failure, not a reason to edit the key.
"""

from __future__ import annotations

import json
import statistics
from pathlib import Path

import pytest

from lexishield.agents.orchestrator import run_analysis
from lexishield.ingest.pipeline import ingest_pdf, ingest_text
from lexishield.llm.gateway import LLMGateway
from lexishield.models import AnalyzeRequest, ChecklistStatus
from lexishield.settings import Settings

pytestmark = pytest.mark.phase2

FIXTURES = Path(__file__).parent / "fixtures"
KEYS = json.loads((FIXTURES / "golden_keys.json").read_text(encoding="utf-8"))
SILENT_OK = {ChecklistStatus.NOT_MENTIONED, ChecklistStatus.UNCLEAR}


def _ingest(name: str):  # type: ignore[no-untyped-def]
    data = (FIXTURES / name).read_bytes()
    return ingest_pdf(data, name) if name.endswith(".pdf") else ingest_text(data.decode("utf-8"), name)


async def _run(name: str):  # type: ignore[no-untyped-def]
    settings = Settings()
    gw = LLMGateway(settings)
    events: list[tuple[str, dict]] = []

    async def emit(n: str, data: dict) -> None:
        events.append((n, data))

    report = await run_analysis(gw, settings, _ingest(name), "doc_golden", AnalyzeRequest(), emit, lambda: False)
    return report, events


_CACHE: dict = {}


async def _results() -> dict:
    """Run each golden document once; the tests share the results (each run takes minutes on the GPU)."""
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


async def test_no_silence_is_ever_reported_as_entailed() -> None:
    results = await _results()
    for name, (report, _) in results.items():
        expected = KEYS["documents"][name]["topics"]
        got = {i.topic_id: i.status for i in report.checklist}
        for topic_id, want in expected.items():
            if want == "SILENT":
                assert got.get(topic_id) in SILENT_OK, f"{name} {topic_id}: {got.get(topic_id)}"


async def test_topic_accuracy_meets_the_gate_for_rental() -> None:
    results = await _results()
    correct = total = 0
    lines: list[str] = []
    for name in ("in_rental_11m_leave_license.txt", "in_rental_missing_clauses.pdf"):
        report, _ = results[name]
        c, t, misses = _score(KEYS["documents"][name]["topics"], report)
        correct, total = correct + c, total + t
        lines += [f"{name}: {c}/{t}"] + [f"  {m}" for m in misses]
    rate = correct / total
    print("\n".join(lines), f"\nrental topic accuracy {rate:.0%}")
    assert rate >= 0.8, "\n".join(lines)


async def test_topic_accuracy_meets_the_gate_for_employment() -> None:
    results = await _results()
    name = "in_offer_letter_bond.pdf"
    report, _ = results[name]
    c, t, misses = _score(KEYS["documents"][name]["topics"], report)
    print(f"\n{name}: {c}/{t} ({c / t:.0%})", *misses, sep="\n  ")
    assert c / t >= 0.8, "\n".join(misses)


async def test_events_arrive_in_order() -> None:
    results = await _results()
    for _name, (_, events) in results.items():
        names = [n for n, _ in events]
        first_class = names.index("classification.ready")
        assert all(n in ("warning", "job.stage") for n in names[:first_class])
        for i, n in enumerate(names):
            if n == "card.ready":
                assert names[i - 1] in ("checklist.item", "card.ready")


async def test_median_reading_grade_is_at_most_nine() -> None:
    results = await _results()
    grades = [c.reading_grade for report, _ in results.values() for c in report.cards if c.reading_grade is not None]
    assert grades, "no card has a reading grade"
    median = statistics.median(grades)
    print(f"\nmedian reading grade {median} over {len(grades)} cards")
    assert median <= 9


async def test_every_displayed_citation_is_verified_source_text() -> None:
    results = await _results()
    for name, (report, _) in results.items():
        doc = _ingest(name)
        for item in report.checklist:
            for c in item.evidence:
                assert doc.text[c.char_start : c.char_end] == c.quote, name
        assert report.metrics.unverified_displayed == 0
