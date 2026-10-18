"""Phase 2 hardening: sealed events, cancel while running and queued, severity rules, money in words,
modal negation, and jurisdiction from the governing-law clause. The model is the test double."""

from __future__ import annotations

import json
import time
from pathlib import Path

import pytest

from conftest import FakeOllama, make_client
from lexishield.ingest.pipeline import ingest_text
from lexishield.ingest.quick import governing_law
from lexishield.models import ChecklistStatus, Distortion, MatchType
from lexishield.verify import distortion
from lexishield.verify.facts import extract_facts
from lexishield.verify.severity import SeverityRule, apply_rules

pytestmark = pytest.mark.phase2

API = "/api/v1"
FIXTURE = Path(__file__).parent / "fixtures" / "in_rental_11m_leave_license.txt"


def _text() -> str:
    return FIXTURE.read_text(encoding="utf-8")


def _wait_finished(client, job_id: str, timeout: float = 30.0) -> dict:  # type: ignore[no-untyped-def]
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        job = client.get(f"{API}/jobs/{job_id}").json()
        if job["status"] in ("done", "failed", "cancelled"):
            return job
        time.sleep(0.05)
    raise AssertionError("job did not finish")


# ----------------------------------------------------------------- sealed events


def test_events_are_sealed_in_the_vault(client) -> None:  # type: ignore[no-untyped-def]
    doc_id = client.post(f"{API}/documents/text", json={"text": _text()}).json()["document_id"]
    job_id = client.post(f"{API}/documents/{doc_id}/analyze", json={}).json()["job_id"]
    _wait_finished(client, job_id)
    vault = client.app.state.vault
    blob = vault._blobs[f"events:{job_id}"]  # the stored bytes are ciphertext
    assert b"checklist.item" not in blob and b"Security deposit" not in blob
    assert client.app.state.jobs.events(job_id)[-1][0] == "report.ready"


def test_deleting_the_document_shreds_the_events(client) -> None:  # type: ignore[no-untyped-def]
    doc_id = client.post(f"{API}/documents/text", json={"text": _text()}).json()["document_id"]
    job_id = client.post(f"{API}/documents/{doc_id}/analyze", json={}).json()["job_id"]
    _wait_finished(client, job_id)
    client.delete(f"{API}/documents/{doc_id}")
    assert client.app.state.jobs.events(job_id) == []
    assert f"events:{job_id}" not in client.app.state.vault._keys


# ----------------------------------------------------------------- cancel


@pytest.fixture
def slow_client(settings):  # type: ignore[no-untyped-def]
    # every model call takes 0.25 s, so a job is still running long enough to cancel
    with make_client(settings, FakeOllama(delay=0.25)) as c:
        yield c


def test_cancel_while_running_stops_before_the_report(slow_client) -> None:  # type: ignore[no-untyped-def]
    client = slow_client
    doc_id = client.post(f"{API}/documents/text", json={"text": _text()}).json()["document_id"]
    job_id = client.post(f"{API}/documents/{doc_id}/analyze", json={}).json()["job_id"]
    time.sleep(0.4)  # let it start
    assert client.get(f"{API}/jobs/{job_id}").json()["status"] == "running"
    assert client.post(f"{API}/jobs/{job_id}/cancel").status_code == 200
    job = _wait_finished(client, job_id)
    assert job["status"] == "cancelled"
    assert client.get(f"{API}/documents/{doc_id}/report").status_code == 404  # no report was stored
    names = [n for n, _ in client.app.state.jobs.events(job_id)]
    assert "report.ready" not in names


def test_a_second_analysis_of_the_same_document_is_refused_while_running(slow_client) -> None:  # type: ignore[no-untyped-def]
    client = slow_client
    doc_id = client.post(f"{API}/documents/text", json={"text": _text()}).json()["document_id"]
    first = client.post(f"{API}/documents/{doc_id}/analyze", json={}).json()["job_id"]
    r = client.post(f"{API}/documents/{doc_id}/analyze", json={})
    assert r.status_code == 409 and r.json()["code"] == "CONFLICT"
    assert client.get(f"{API}/documents/{doc_id}/report").json()["code"] == "CONFLICT"
    client.post(f"{API}/jobs/{first}/cancel")
    _wait_finished(client, first)


def test_cancel_a_queued_job_before_it_runs(slow_client) -> None:  # type: ignore[no-untyped-def]
    client = slow_client
    a = client.post(f"{API}/documents/text", json={"text": _text()}).json()["document_id"]
    b = client.post(f"{API}/documents/text", json={"text": _text()}).json()["document_id"]
    job_a = client.post(f"{API}/documents/{a}/analyze", json={}).json()["job_id"]
    job_b = client.post(f"{API}/documents/{b}/analyze", json={}).json()["job_id"]  # waits for the GPU lock
    assert client.get(f"{API}/jobs/{job_b}").json()["status"] == "queued"
    assert client.post(f"{API}/jobs/{job_b}/cancel").json()["status"] == "cancelled"
    assert client.get(f"{API}/documents/{b}/report").status_code == 404
    client.post(f"{API}/jobs/{job_a}/cancel")
    _wait_finished(client, job_a)
    time.sleep(0.2)
    assert client.get(f"{API}/jobs/{job_b}").json()["status"] == "cancelled"  # never started


# ----------------------------------------------------------------- severity rules


def test_severity_rule_raises_severity_when_the_fact_is_over_the_limit() -> None:
    rule = SeverityRule.model_validate({"when": {"fact_unit": "months", "gt": 6}, "then": {"severity": "HIGH"}})
    assert apply_rules([rule], ChecklistStatus.ENTAILED, {"months 11"}, _sev("MEDIUM")) == (_sev("HIGH"), None)
    assert apply_rules([rule], ChecklistStatus.ENTAILED, {"months 6"}, _sev("MEDIUM"))[0] == _sev("MEDIUM")
    assert apply_rules([rule], ChecklistStatus.ENTAILED, {"INR 150000"}, _sev("MEDIUM"))[0] == _sev("MEDIUM")


def test_severity_rule_on_status_and_first_match_wins() -> None:
    rules = [
        SeverityRule.model_validate({"when": {"status": "NOT_MENTIONED"}, "then": {"severity": "HIGH", "note": "A"}}),
        SeverityRule.model_validate({"when": {"status": "NOT_MENTIONED"}, "then": {"severity": "LOW", "note": "B"}}),
    ]
    assert apply_rules(rules, ChecklistStatus.NOT_MENTIONED, set(), _sev("MEDIUM")) == (_sev("HIGH"), "A")
    assert apply_rules(rules, ChecklistStatus.ENTAILED, set(), _sev("MEDIUM")) == (_sev("MEDIUM"), None)


def _sev(name: str):  # type: ignore[no-untyped-def]
    from lexishield.models import Severity

    return Severity(name)


def test_the_lock_in_rule_is_in_the_pack_and_raises_a_long_lock_in() -> None:
    from lexishield.packs import all_packs
    from lexishield.settings import Settings

    topic = next(t for t in all_packs(Settings())["in_rental"].topics if t.id == "in_rental.lock_in")
    sev, note = apply_rules(topic.severity_rules, ChecklistStatus.ENTAILED, {"months 12"}, topic.severity)
    assert sev.value == "HIGH" and note


# ----------------------------------------------------------------- money in words, modal negation


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("Rs. 1,50,000/- (Rupees One Lakh Fifty Thousand only)", {"INR 150000"}),
        ("Rupees Two Hundred Thousand only", {"INR 200000"}),
        ("Rupees Fifteen Thousand", {"INR 15000"}),
    ],
)
def test_amounts_written_in_words_are_facts(text: str, expected: set[str]) -> None:
    assert expected <= extract_facts(text)


def test_interest_free_and_no_interest_do_not_trigger_a_negation_warning() -> None:
    from lexishield.models import Citation

    source = "The Licensee shall pay an interest-free refundable security deposit of Rs. 1,50,000/-."
    cit = Citation(page=1, char_start=0, char_end=len(source), clause_id="C4", quote=source, match=MatchType.EXACT)
    result, _ = distortion.check("You pay Rs. 1,50,000 and no interest is earned.", [cit], {})
    assert result == Distortion.PASS


def test_shall_not_against_must_still_warns() -> None:
    from lexishield.models import Citation

    source = "The Licensee shall not sublet the Premises."
    cit = Citation(page=1, char_start=0, char_end=len(source), clause_id="C7", quote=source, match=MatchType.EXACT)
    assert distortion.check("The tenant must sublet the Premises.", [cit], {})[0] == Distortion.WARN


# ----------------------------------------------------------------- jurisdiction from the governing law


@pytest.mark.parametrize(
    ("clause", "country"),
    [
        ("This Agreement is governed by the laws of India, and courts at Bengaluru have jurisdiction.", "IN"),
        ("This tenancy is governed by the laws of England and Wales.", "UK"),
        ("This lease is governed by the laws of the State of California.", "US"),
    ],
)
def test_governing_law_names_the_country(clause: str, country: str) -> None:
    law = governing_law(clause)
    assert law is not None and law[0].value == country


def test_report_jurisdiction_cites_the_governing_law_clause(client) -> None:  # type: ignore[no-untyped-def]
    doc_id = client.post(f"{API}/documents/text", json={"text": _text()}).json()["document_id"]
    job_id = client.post(f"{API}/documents/{doc_id}/analyze", json={}).json()["job_id"]
    _wait_finished(client, job_id)
    rep = client.get(f"{API}/documents/{doc_id}/report").json()
    assert rep["jurisdiction"]["country"] == "IN" and rep["jurisdiction"]["confidence"] == 0.9
    ev = rep["jurisdiction"]["evidence"]
    assert ev and "governed by the laws of India" in ev[0]["quote"]
    ing = ingest_text(_text())
    assert ing.text[ev[0]["char_start"] : ev[0]["char_end"]] == ev[0]["quote"]
    assert json.dumps(rep)  # the report serializes
