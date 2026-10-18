"""Capture real analysis output on the synthetic rental fixture, for the frontend contract examples.

The report, card and silent checklist item in contracts/examples/ come from this file, not from hand-written
objects, so the frontend sees what the analysis really produces. Run it once on a machine with the model:

  uv run python scripts/capture_examples.py

It writes scripts/captured/*.json, which scripts/contract_examples.py reads. Commit the captured files. Re-run this
only when the report shape changes; the examples then change with it.
"""

from __future__ import annotations

import asyncio
from pathlib import Path

from lexishield.agents.orchestrator import run_analysis
from lexishield.ingest.pipeline import ingest_text
from lexishield.llm.gateway import LLMGateway
from lexishield.models import AnalyzeRequest, ChecklistStatus
from lexishield.settings import Settings

CAPTURED = Path(__file__).resolve().parent / "captured"
FIXTURE = Path(__file__).resolve().parents[1] / "tests" / "fixtures" / "in_rental_11m_leave_license.txt"
EXAMPLE_DOC = "doc_example"


async def main() -> None:
    settings = Settings()
    gw = LLMGateway(settings)
    ing = ingest_text(FIXTURE.read_text(encoding="utf-8"), FIXTURE.name)

    async def emit(name: str, data: dict) -> None:  # the captured report is what matters, not the stream
        return None

    report = await run_analysis(gw, settings, ing, EXAMPLE_DOC, AnalyzeRequest(), emit, lambda: False)
    card = next(c for c in report.cards if c.plain_explanation is not None)
    silent = next(i for i in report.checklist if i.status == ChecklistStatus.NOT_MENTIONED)

    CAPTURED.mkdir(parents=True, exist_ok=True)
    (CAPTURED / "report.json").write_text(report.model_dump_json(indent=2) + "\n", encoding="utf-8")
    (CAPTURED / "card.json").write_text(card.model_dump_json(indent=2) + "\n", encoding="utf-8")
    (CAPTURED / "checklist_item_silent.json").write_text(silent.model_dump_json(indent=2) + "\n", encoding="utf-8")
    print(f"captured to {CAPTURED}: {len(report.checklist)} items, {len(report.cards)} cards")


if __name__ == "__main__":
    asyncio.run(main())
