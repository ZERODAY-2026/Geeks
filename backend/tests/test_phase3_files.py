"""Phase 3 source viewer support: line numbers on citations, and the original uploaded file. No model needed."""

from __future__ import annotations

import io
import json
from pathlib import Path

import pytest
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas

from conftest import FakeOllama
from lexishield.agents.ask import answer
from lexishield.ingest.pipeline import ingest_text
from lexishield.ingest.segment import line_span
from lexishield.llm.gateway import LLMGateway
from lexishield.models import AskRequest, AskStatus, PageText
from lexishield.settings import Settings
from lexishield.verify.quotes import verify_quote

pytestmark = pytest.mark.phase3

API = "/api/v1"
FIXTURE = Path(__file__).parent / "fixtures" / "in_rental_11m_leave_license.txt"
DEPOSIT = "The Licensee shall pay to the Licensor an interest-free refundable security deposit of Rs. 1,50,000/-"


def _line_of(text: str, offset: int) -> int:
    return text.count("\n", 0, offset) + 1


# ----------------------------------------------------------------- line numbers


def test_line_span_counts_lines_within_the_page() -> None:
    page1 = "line one\nline two\nline three"
    page2 = "next page first\nnext page second"
    pages = [
        PageText(page=1, text=page1, char_start=0, char_end=len(page1)),
        PageText(page=2, text=page2, char_start=len(page1) + 2, char_end=len(page1) + 2 + len(page2)),
    ]
    assert line_span(pages, page1.index("two"), page1.index("two") + 3) == (2, 2)
    assert line_span(pages, page1.index("line two"), len(page1)) == (2, 3)
    start2 = pages[1].char_start + page2.index("second")
    assert line_span(pages, start2, start2 + 6) == (2, 2)  # counted on page 2, not from the top of the document


def test_verified_citations_carry_their_lines() -> None:
    text = FIXTURE.read_text(encoding="utf-8")
    ing = ingest_text(text)
    clause = next(c for c in ing.clauses if c.number == "3")
    cit = verify_quote(DEPOSIT, clause, ing.text, ing.pages)
    assert cit is not None
    assert cit.line_start == _line_of(text, cit.char_start)
    assert cit.line_end == _line_of(text, cit.char_end - 1)


async def test_ask_citations_carry_their_lines() -> None:
    text = FIXTURE.read_text(encoding="utf-8")
    ing = ingest_text(text)
    clause_id = next(c.id for c in ing.clauses if c.number == "3")
    reply = json.dumps(
        {
            "claims": [
                {"text": "The deposit is Rs. 1,50,000.", "evidence": [{"clause_id": clause_id, "quote": DEPOSIT}]}
            ],
            "status": "ANSWERED",
        }
    )
    gw = LLMGateway(Settings(), client=FakeOllama(replies=[reply, json.dumps({"addresses_topic": True})]))
    resp = await answer(gw, Settings(), ing, None, AskRequest(question="How much is the security deposit?"))
    assert resp.status == AskStatus.ANSWERED
    cit = resp.claims[0].citations[0]
    assert cit.page == 1 and cit.line_start == _line_of(text, cit.char_start)
    for related in resp.related_clauses:
        assert related.line_start is not None and related.line_end is not None


# ----------------------------------------------------------------- original file


def _pdf() -> bytes:
    buf = io.BytesIO()
    c = canvas.Canvas(buf, pagesize=A4)
    c.drawString(72, 760, "1. TERM. The licence is for eleven (11) months.")
    c.save()
    return buf.getvalue()


def _docx() -> bytes:
    import docx

    d = docx.Document()
    d.add_paragraph("1. TERM. The licence is for eleven (11) months.")
    buf = io.BytesIO()
    d.save(buf)
    return buf.getvalue()


@pytest.mark.parametrize(
    ("name", "data", "mime"),
    [
        ("lease.pdf", _pdf(), "application/pdf"),
        ("lease.docx", _docx(), "application/vnd.openxmlformats-officedocument.wordprocessingml.document"),
        ("lease.txt", b"1. TERM. The licence is for eleven (11) months.\n", "text/plain"),
    ],
)
def test_the_original_file_comes_back_unchanged(client, name: str, data: bytes, mime: str) -> None:  # type: ignore[no-untyped-def]
    doc_id = client.post(f"{API}/documents", files={"file": (name, data, "application/octet-stream")}).json()[
        "document_id"
    ]
    r = client.get(f"{API}/documents/{doc_id}/file")
    assert r.status_code == 200
    assert r.content == data
    assert r.headers["content-type"].startswith(mime)
    assert r.headers["content-disposition"].startswith("inline")
    assert r.headers["cache-control"] == "no-store"


def test_pasted_text_is_served_as_text(client) -> None:  # type: ignore[no-untyped-def]
    doc_id = client.post(f"{API}/documents/text", json={"text": "1. TERM. Eleven months."}).json()["document_id"]
    r = client.get(f"{API}/documents/{doc_id}/file")
    assert r.status_code == 200 and r.text == "1. TERM. Eleven months."


def test_the_file_is_shredded_with_the_document(client) -> None:  # type: ignore[no-untyped-def]
    doc_id = client.post(f"{API}/documents/text", json={"text": "1. TERM. Eleven months."}).json()["document_id"]
    assert client.delete(f"{API}/documents/{doc_id}").status_code == 200
    assert client.get(f"{API}/documents/{doc_id}/file").status_code == 404
    assert f"file:{doc_id}" not in client.app.state.vault.ids()


def test_wipe_counts_documents_not_sealed_entries(client) -> None:  # type: ignore[no-untyped-def]
    client.delete(f"{API}/sessions")
    for text in ("1. TERM. Eleven months.", "2. FEE. Rs. 5,000."):
        client.post(f"{API}/documents/text", json={"text": text})
    assert client.delete(f"{API}/sessions").json()["wiped"] == 2  # each document also has a stored file
