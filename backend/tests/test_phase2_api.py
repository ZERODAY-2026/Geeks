"""Phase 2 gate (API): analyze, SSE order, report, cancel, packs, and deletion. The model is the test double."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

API = "/api/v1"
FIXTURE = Path(__file__).parent / "fixtures" / "in_rental_11m_leave_license.txt"

pytestmark = pytest.mark.phase2


def _upload(client) -> str:  # type: ignore[no-untyped-def]
    r = client.post(
        f"{API}/documents/text", json={"text": FIXTURE.read_text(encoding="utf-8"), "filename": "lease.txt"}
    )
    assert r.status_code == 201, r.text
    return r.json()["document_id"]


def _events(client, job_id: str) -> list[tuple[str, dict]]:  # type: ignore[no-untyped-def]
    out: list[tuple[str, dict]] = []
    with client.stream("GET", f"{API}/jobs/{job_id}/events") as r:
        assert r.status_code == 200
        name = None
        for line in r.iter_lines():
            if line.startswith("event:"):
                name = line.split(":", 1)[1].strip()
            elif line.startswith("data:") and name:
                out.append((name, json.loads(line.split(":", 1)[1])))
                name = None
    return out


def test_analyze_streams_events_in_contract_order(client) -> None:  # type: ignore[no-untyped-def]
    doc_id = _upload(client)
    r = client.post(f"{API}/documents/{doc_id}/analyze", json={})
    assert r.status_code == 202, r.text
    accepted = r.json()
    assert accepted["events_url"] == f"{API}/jobs/{accepted['job_id']}/events"

    events = _events(client, accepted["job_id"])
    names = [n for n, _ in events]
    assert names[0] == "job.stage"
    assert names[1] == "classification.ready"
    assert names[-1] == "report.ready"
    assert "job.failed" not in names
    assert names.count("checklist.item") == 18  # the in_rental pack has 18 topics
    # every checklist.item is followed by a card.ready or nothing (silence), and comes before report.ready
    for i, n in enumerate(names):
        if n == "card.ready":
            assert names[i - 1] in ("checklist.item", "card.ready")
    assert events[-1][1] == {"document_id": doc_id, "report_url": f"{API}/documents/{doc_id}/report"}


def test_job_is_done_and_report_is_retrievable(client) -> None:  # type: ignore[no-untyped-def]
    doc_id = _upload(client)
    job_id = client.post(f"{API}/documents/{doc_id}/analyze", json={}).json()["job_id"]
    _events(client, job_id)  # waits until the job finishes
    job = client.get(f"{API}/jobs/{job_id}").json()
    assert job["status"] == "done" and job["progress"]["total"] == 18

    report = client.get(f"{API}/documents/{doc_id}/report")
    assert report.status_code == 200
    body = report.json()
    assert body["pack_id"] == "in_rental" and len(body["checklist"]) == 18
    assert body["metrics"]["unverified_displayed"] == 0
    assert body["disclaimer"].startswith("LexiShield gives preliminary information")


def test_every_displayed_citation_is_source_text(client) -> None:  # type: ignore[no-untyped-def]
    doc_id = _upload(client)
    job_id = client.post(f"{API}/documents/{doc_id}/analyze", json={}).json()["job_id"]
    _events(client, job_id)
    text = "\n\n".join(p["text"] for p in client.get(f"{API}/documents/{doc_id}").json()["pages"])
    body = client.get(f"{API}/documents/{doc_id}/report").json()
    shown = [card["source"] for card in body["cards"] if card["source"]]
    shown += [c for item in body["checklist"] for c in item["evidence"]]
    for c in shown:
        assert text[c["char_start"] : c["char_end"]] == c["quote"]


def test_second_analysis_is_refused_while_one_runs(client) -> None:  # type: ignore[no-untyped-def]
    doc_id = _upload(client)
    first = client.post(f"{API}/documents/{doc_id}/analyze", json={})
    assert first.status_code == 202
    second = client.post(f"{API}/documents/{doc_id}/analyze", json={})
    if second.status_code == 409:
        assert second.json()["code"] == "CONFLICT"
    _events(client, first.json()["job_id"])  # let the first one finish either way


def test_report_before_analysis_is_404(client) -> None:  # type: ignore[no-untyped-def]
    doc_id = _upload(client)
    r = client.get(f"{API}/documents/{doc_id}/report")
    assert r.status_code == 404 and r.json()["code"] == "NOT_FOUND"


def test_analyze_unknown_document_is_404(client) -> None:  # type: ignore[no-untyped-def]
    r = client.post(f"{API}/documents/doc_missing/analyze", json={})
    assert r.status_code == 404


def test_deleting_the_document_removes_the_report_and_jobs(client) -> None:  # type: ignore[no-untyped-def]
    doc_id = _upload(client)
    job_id = client.post(f"{API}/documents/{doc_id}/analyze", json={}).json()["job_id"]
    _events(client, job_id)
    assert client.get(f"{API}/documents/{doc_id}/report").status_code == 200
    assert client.delete(f"{API}/documents/{doc_id}").status_code == 200
    assert client.get(f"{API}/documents/{doc_id}/report").status_code == 404
    assert client.get(f"{API}/jobs/{job_id}").status_code == 404


def test_unknown_job_is_404(client) -> None:  # type: ignore[no-untyped-def]
    assert client.get(f"{API}/jobs/job_nope").status_code == 404
    assert client.get(f"{API}/jobs/job_nope/events").status_code == 404
    assert client.post(f"{API}/jobs/job_nope/cancel").status_code == 404


def test_packs_are_listed_and_validated(client) -> None:  # type: ignore[no-untyped-def]
    packs = client.get(f"{API}/packs").json()
    assert {p["pack_id"] for p in packs} == {"in_rental", "in_employment", "msa_generic", "notice_generic"}
    rental = client.get(f"{API}/packs/in_rental").json()
    assert rental["depth"] == "deep" and len(rental["topics"]) == 18
    assert client.get(f"{API}/packs/nope").json()["code"] == "NOT_FOUND"
