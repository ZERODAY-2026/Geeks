"""Phase 1 gate (API + trust): upload, read, clause, crypto-shred delete, egress guard, privacy endpoints."""

from __future__ import annotations

import io
import socket
from pathlib import Path

import pytest
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas

from lexishield.trust import egress_guard
from lexishield.trust.egress_guard import EgressBlocked

pytestmark = pytest.mark.phase1

API = "/api/v1"
FIXTURE = Path(__file__).parent / "fixtures" / "in_rental_11m_leave_license.txt"


@pytest.fixture
def doc_id(client) -> str:  # type: ignore[no-untyped-def]
    r = client.post(
        f"{API}/documents/text", json={"text": FIXTURE.read_text(encoding="utf-8"), "filename": "lease.txt"}
    )
    assert r.status_code == 201, r.text
    return r.json()["document_id"]


def test_upload_text_returns_summary(client) -> None:  # type: ignore[no-untyped-def]
    r = client.post(f"{API}/documents/text", json={"text": FIXTURE.read_text(encoding="utf-8")})
    assert r.status_code == 201
    s = r.json()
    assert s["document_id"].startswith("doc_") and s["clause_count"] == 10
    assert s["quick_detect"] == {"doc_type": "rental", "country": "IN"}
    assert s["scanned"] is False


def test_read_document_clauses_match_source_offsets(client, doc_id) -> None:  # type: ignore[no-untyped-def]
    d = client.get(f"{API}/documents/{doc_id}").json()
    page_text = d["pages"][0]["text"]
    for c in d["clauses"]:
        assert page_text[c["char_start"] : c["char_end"]] == c["text"]


def test_single_clause_endpoint(client, doc_id) -> None:  # type: ignore[no-untyped-def]
    r = client.get(f"{API}/documents/{doc_id}/clauses/C4")
    assert r.status_code == 200 and r.json()["heading"] == "SECURITY DEPOSIT"
    assert client.get(f"{API}/documents/{doc_id}/clauses/C99").json()["code"] == "NOT_FOUND"


def test_delete_crypto_shreds_and_document_is_gone(client, doc_id) -> None:  # type: ignore[no-untyped-def]
    r = client.delete(f"{API}/documents/{doc_id}")
    assert r.json() == {"deleted": True, "crypto_shredded": True}
    assert client.get(f"{API}/documents/{doc_id}").status_code == 404
    assert client.delete(f"{API}/documents/{doc_id}").status_code == 404


def test_wipe_sessions(client) -> None:  # type: ignore[no-untyped-def]
    client.post(f"{API}/documents/text", json={"text": "1. TERM. Eleven months."})
    client.post(f"{API}/documents/text", json={"text": "2. FEE. Rs. 5,000."})
    assert client.delete(f"{API}/sessions").json()["wiped"] >= 2


def test_docx_is_refused_with_problem_json(client) -> None:  # type: ignore[no-untyped-def]
    r = client.post(f"{API}/documents", files={"file": ("lease.docx", b"PK\x03\x04", "application/octet-stream")})
    assert r.status_code == 415 and r.json()["code"] == "UNSUPPORTED_TYPE"


def test_pdf_upload_via_multipart(client) -> None:  # type: ignore[no-untyped-def]
    buf = io.BytesIO()
    c = canvas.Canvas(buf, pagesize=A4)
    c.setFont("Helvetica", 11)
    c.drawString(72, 760, "1. TERM. The licence is for eleven (11) months.")
    c.drawString(72, 740, "2. SECURITY DEPOSIT. Rs. 1,50,000/- is refundable.")
    c.save()
    r = client.post(f"{API}/documents", files={"file": ("lease.pdf", buf.getvalue(), "application/pdf")})
    assert r.status_code == 201 and r.json()["clause_count"] == 2 and r.json()["mime"] == "application/pdf"


def test_corrupt_pdf_upload_is_422(client) -> None:  # type: ignore[no-untyped-def]
    r = client.post(f"{API}/documents", files={"file": ("x.pdf", b"garbage", "application/pdf")})
    assert r.status_code == 422 and r.json()["code"] == "MALFORMED_FILE"


def test_oversize_upload_is_413(client, settings) -> None:  # type: ignore[no-untyped-def]
    settings.server.max_upload_mb = 0
    r = client.post(f"{API}/documents", files={"file": ("big.txt", b"x" * 10, "text/plain")})
    assert r.status_code == 413 and r.json()["code"] == "DOC_TOO_LARGE"


def test_egress_guard_blocks_external_connection() -> None:
    before = egress_guard.status()["blocked_attempts"]
    with pytest.raises(EgressBlocked):
        socket.create_connection(("example.com", 443), timeout=2)
    assert egress_guard.status()["blocked_attempts"] == before + 1
    assert any(e["target"] == "example.com" for e in egress_guard.events())


def test_loopback_is_allowed() -> None:
    srv = socket.socket()
    srv.bind(("127.0.0.1", 0))
    srv.listen(1)
    port = srv.getsockname()[1]
    conn = socket.create_connection(("127.0.0.1", port), timeout=2)  # must not raise
    conn.close()
    srv.close()


def test_privacy_status_and_events(client, doc_id) -> None:  # type: ignore[no-untyped-def]
    st = client.get(f"{API}/privacy/status").json()
    assert st["egress_guard"]["active"] is True
    assert "127.0.0.1" in st["egress_guard"]["allowed_hosts"]
    assert st["network_mode"] == "host-loopback" and st["sessions"] >= 1
    ev = client.get(f"{API}/privacy/events").json()
    assert isinstance(ev, list)
    assert all(set(e) >= {"ts", "type", "action"} for e in ev)
