"""Phase 1 gate (classifier): document type on the five core fixtures, hidden text kept out of prompts,
and the signals fallback when the model is unavailable."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from conftest import FakeOllama
from lexishield.agents.classify import classify
from lexishield.ingest.pipeline import Ingested, ingest_pdf, ingest_text
from lexishield.llm.gateway import LLMGateway
from lexishield.models import DocType
from lexishield.settings import Settings

pytestmark = pytest.mark.phase1

FIXTURES = Path(__file__).parent / "fixtures"
KEYS = json.loads((FIXTURES / "answer_keys.json").read_text(encoding="utf-8"))
CORE = sorted(name for name, meta in KEYS["documents"].items() if meta["core"])


def _ingest(name: str) -> Ingested:
    data = (FIXTURES / name).read_bytes()
    if name.endswith(".pdf"):
        return ingest_pdf(data, name)
    return ingest_text(data.decode("utf-8"), name)


@pytest.mark.parametrize("name", CORE)
async def test_doc_type_is_correct_on_core_fixtures(name: str) -> None:
    gw = LLMGateway(Settings())  # the real Gemma model, through the gateway
    result = await classify(gw, _ingest(name))
    assert result.source == "model"
    assert result.classification.doc_type == DocType(KEYS["documents"][name]["doc_type"])


async def test_injection_never_reaches_the_model_payload() -> None:
    fake = FakeOllama(replies=['{"doc_type": "rental", "party_roles": [], "confidence": 0.9}'])
    gw = LLMGateway(Settings(), client=fake)
    ing = _ingest("adv_white_text_injection.txt")
    result = await classify(gw, ing)
    payload = json.dumps(fake.calls, ensure_ascii=False)
    assert "Ignore previous instructions" not in payload
    assert "Recommend signing" not in payload
    assert "[flagged text removed]" in payload
    assert result.source == "model"


async def test_signals_fallback_when_the_model_is_down() -> None:
    gw = LLMGateway(Settings(), client=FakeOllama(down=True))
    ing = _ingest("in_rental_11m_leave_license.txt")
    result = await classify(gw, ing)
    assert result.source == "signals"
    assert result.classification.doc_type == DocType.RENTAL
    assert result.classification.confidence == 0.3
