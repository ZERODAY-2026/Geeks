"""Phase 2 grounding gate: a verified quote must itself address the topic question, judged per quote by the model.

The fresh held-out run showed a claim (subletting) supported by a quote about occupancy. The quote was real, so the
verifier passed it. The relevance check asks the model, one quote at a time, whether the quote addresses the topic.
If it does not, the quote is not kept, and an ENTAILED or CONTRADICTED answer with no kept quote becomes UNCLEAR.
A failed check keeps nothing. The gate can be switched off, which is how the before-and-after comparison runs.
"""

from __future__ import annotations

import json

import pytest

from conftest import FakeOllama
from lexishield.agents.checklist import DocContext, analyze_topic
from lexishield.ingest.pipeline import ingest_text
from lexishield.llm.gateway import LLMGateway
from lexishield.models import ChecklistStatus, Country, UserRole
from lexishield.packs import all_packs
from lexishield.settings import Settings

pytestmark = pytest.mark.phase2

TEXT = (
    "1. OCCUPANCY. Only the Tenant and immediate family may live in the flat.\n"
    "2. SUBLETTING. The Tenant shall not sublet the flat to anyone else.\n"
)
OFF_TOPIC = "Only the Tenant and immediate family may live in the flat."
ON_TOPIC = "The Tenant shall not sublet the flat to anyone else."


def _subletting():  # type: ignore[no-untyped-def]
    pack = next(p for p in all_packs(Settings()).values() if any(t.id == "in_rental.subletting" for t in p.topics))
    return next(t for t in pack.topics if t.id == "in_rental.subletting")


def _doc(gate: bool) -> DocContext:
    ing = ingest_text(TEXT)
    return DocContext.build(ing, {}, Country.IN, 92, 6, relevance_gate=gate)


def _claim(clause_id: str, quote: str) -> str:
    return json.dumps(
        {
            "status": "ENTAILED",
            "evidence": [{"clause_id": clause_id, "quote": quote}],
            "plain_explanation": "The tenant may not sublet the flat.",
            "stated": [],
            "interpretations": [],
        }
    )


async def test_a_quote_that_does_not_address_the_topic_is_dropped() -> None:
    doc = _doc(gate=True)
    occupancy = doc.ing.clauses[0].id
    gw = LLMGateway(
        Settings(),
        client=FakeOllama(replies=[_claim(occupancy, OFF_TOPIC), json.dumps({"addresses_topic": False})]),
    )
    out = await analyze_topic(gw, _subletting(), doc, UserRole.TENANT)
    assert out.item.status == ChecklistStatus.UNCLEAR
    assert out.item.evidence == []
    assert occupancy in out.dropped


async def test_a_quote_that_addresses_the_topic_keeps_the_claim() -> None:
    doc = _doc(gate=True)
    sublet = doc.ing.clauses[1].id
    gw = LLMGateway(
        Settings(),
        client=FakeOllama(replies=[_claim(sublet, ON_TOPIC), json.dumps({"addresses_topic": True})]),
    )
    out = await analyze_topic(gw, _subletting(), doc, UserRole.TENANT)
    assert out.item.status == ChecklistStatus.ENTAILED
    assert len(out.item.evidence) == 1


async def test_a_failed_relevance_check_keeps_nothing() -> None:
    doc = _doc(gate=True)
    sublet = doc.ing.clauses[1].id
    gw = LLMGateway(Settings(), client=FakeOllama(replies=[_claim(sublet, ON_TOPIC)]))  # no relevance answer
    out = await analyze_topic(gw, _subletting(), doc, UserRole.TENANT)
    assert out.item.status == ChecklistStatus.UNCLEAR
    assert out.item.evidence == []


async def test_with_the_gate_off_the_old_behaviour_returns() -> None:
    doc = _doc(gate=False)
    occupancy = doc.ing.clauses[0].id
    gw = LLMGateway(Settings(), client=FakeOllama(replies=[_claim(occupancy, OFF_TOPIC)]))
    out = await analyze_topic(gw, _subletting(), doc, UserRole.TENANT)
    assert out.item.status == ChecklistStatus.ENTAILED  # the baseline the comparison measures against
