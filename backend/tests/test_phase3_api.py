"""Phase 3 gate (API): ask, scenarios, statutes and brief through the routes. The model is the test double."""

from __future__ import annotations

import sqlite3

import pytest

from lexishield.models import Country
from lexishield.triage.statutes import act_key, section_key
from reports import EMPLOYMENT_TEXT, employment_report

pytestmark = pytest.mark.phase3

API = "/api/v1"


def _upload(client) -> str:  # type: ignore[no-untyped-def]
    r = client.post(f"{API}/documents/text", json={"text": EMPLOYMENT_TEXT, "filename": "offer.txt"})
    assert r.status_code == 201, r.text
    return r.json()["document_id"]


def _store(client, doc_id: str, country: Country = Country.IN) -> None:  # type: ignore[no-untyped-def]
    _, report = employment_report(doc_id, country)
    client.app.state.jobs.store_report(report)


def test_ask_works_before_analysis(client) -> None:  # type: ignore[no-untyped-def]
    doc_id = _upload(client)
    r = client.post(f"{API}/documents/{doc_id}/ask", json={"question": "Is the bond enforceable?"})
    assert r.status_code == 200 and r.json()["status"] == "LEGAL_VERDICT_DECLINED"


def test_ask_on_a_missing_document_is_404(client) -> None:  # type: ignore[no-untyped-def]
    assert client.post(f"{API}/documents/doc_nope/ask", json={"question": "Hi?"}).status_code == 404


def test_scenarios_are_listed_by_document_type(client) -> None:  # type: ignore[no-untyped-def]
    ids = {s["scenario_id"] for s in client.get(f"{API}/scenarios", params={"doc_type": "employment"}).json()}
    assert ids == {"bond_exit"}
    assert len(client.get(f"{API}/scenarios").json()) == 3


def test_a_scenario_needs_an_analysis_first(client) -> None:  # type: ignore[no-untyped-def]
    doc_id = _upload(client)
    r = client.post(f"{API}/documents/{doc_id}/scenarios/bond_exit/run", json={"params": {"months_served": 3}})
    assert r.status_code == 409 and r.json()["code"] == "CONFLICT"


def test_a_scenario_runs_on_the_stored_report(client) -> None:  # type: ignore[no-untyped-def]
    doc_id = _upload(client)
    _store(client, doc_id)
    r = client.post(f"{API}/documents/{doc_id}/scenarios/bond_exit/run", json={"params": {"months_served": 3}})
    assert r.status_code == 200
    assert r.json()["exposure"]["computable"] is True and r.json()["exposure"]["total"] == 200000
    assert client.post(f"{API}/documents/{doc_id}/scenarios/nope/run", json={"params": {}}).status_code == 404


def test_statutes_without_the_index_say_so(client, settings, tmp_path) -> None:  # type: ignore[no-untyped-def]
    settings.paths.data_dir = str(tmp_path)  # no statutes.sqlite here
    doc_id = _upload(client)
    _store(client, doc_id)
    r = client.get(f"{API}/documents/{doc_id}/statutes")
    assert r.status_code == 409 and r.json()["code"] == "STATUTE_INDEX_UNAVAILABLE"


def _synthetic_index(path) -> None:  # type: ignore[no-untyped-def]
    """A two-row index with made-up text, to test the lookup. It is not legal text."""
    with sqlite3.connect(path) as conn:
        conn.execute(
            "CREATE TABLE sections (act_key TEXT, section_key TEXT, act TEXT, section TEXT, title TEXT, text TEXT, "
            "status TEXT, source_url TEXT, PRIMARY KEY (act_key, section_key))"
        )
        conn.execute("CREATE TABLE meta (key TEXT PRIMARY KEY, value TEXT)")
        for section in ("27", "74"):
            conn.execute(
                "INSERT INTO sections VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                (
                    act_key("Indian Contract Act, 1872"),
                    section_key(section),
                    "Indian Contract Act, 1872",
                    section,
                    "Synthetic title",
                    "Synthetic test text, not the statute.",
                    "in force",
                    None,
                ),
            )
        conn.execute("INSERT INTO meta VALUES ('snapshot', 'test-snapshot')")


def test_statutes_come_from_the_index_with_the_snapshot(client, settings, tmp_path) -> None:  # type: ignore[no-untyped-def]
    settings.paths.data_dir = str(tmp_path)
    _synthetic_index(tmp_path / "statutes.sqlite")
    doc_id = _upload(client)
    _store(client, doc_id)
    refs = client.get(f"{API}/documents/{doc_id}/statutes").json()
    assert {(r["topic_id"], r["section"]) for r in refs} == {
        ("in_employment.non_compete", "27"),
        ("in_employment.service_bond", "74"),
    }
    assert all(r["snapshot"] == "test-snapshot" and r["note"] for r in refs)


def test_statutes_are_empty_outside_india(client, settings, tmp_path) -> None:  # type: ignore[no-untyped-def]
    settings.paths.data_dir = str(tmp_path)
    _synthetic_index(tmp_path / "statutes.sqlite")
    doc_id = _upload(client)
    _store(client, doc_id, Country.UK)
    assert client.get(f"{API}/documents/{doc_id}/statutes").json() == []


def test_brief_in_json_and_markdown(client) -> None:  # type: ignore[no-untyped-def]
    doc_id = _upload(client)
    assert client.get(f"{API}/documents/{doc_id}/brief").status_code == 409  # before analysis
    _store(client, doc_id)
    body = client.get(f"{API}/documents/{doc_id}/brief").json()
    assert body["document_id"] == doc_id
    assert "in_employment.joining_bonus_clawback" in body["silences"]
    md = client.get(f"{API}/documents/{doc_id}/brief", params={"format": "md"})
    assert md.status_code == 200 and md.headers["content-type"].startswith("text/markdown")
    assert md.text.startswith("# Brief for a lawyer") and "not legal advice" in md.text
