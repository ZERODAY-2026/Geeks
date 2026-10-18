"""Smoke-test a RUNNING LexiShield API, phase by phase (part of each run-test gate).

Usage:
  uv run lexishield serve --profile cpu        # in another terminal
  uv run python scripts/smoke_api.py --phase 0 [--base http://127.0.0.1:8000]
"""

from __future__ import annotations

import argparse
import sys
from collections.abc import Callable
from pathlib import Path

import httpx

API = "/api/v1"
PLANNED_PATHS = [
    "/health",
    "/system/info",
    "/system/benchmark",
    "/privacy/status",
    "/privacy/events",
    "/privacy/receipts",
    "/documents",
    "/documents/text",
    "/documents/{document_id}",
    "/documents/{document_id}/clauses/{clause_id}",
    "/sessions",
    "/documents/{document_id}/analyze",
    "/jobs/{job_id}",
    "/jobs/{job_id}/events",
    "/jobs/{job_id}/cancel",
    "/documents/{document_id}/report",
    "/documents/{document_id}/ask",
    "/scenarios",
    "/documents/{document_id}/scenarios/{scenario_id}/run",
    "/documents/{document_id}/statutes",
    "/documents/{document_id}/brief",
    "/packs",
    "/packs/{pack_id}",
    "/eval/summary",
]


class Smoke:
    def __init__(self, base: str) -> None:
        self.c = httpx.Client(base_url=base, timeout=30)
        self.results: list[tuple[str, bool, str]] = []

    def check(self, name: str, fn: Callable[[], str]) -> None:
        try:
            self.results.append((name, True, fn()))
        except AssertionError as e:
            self.results.append((name, False, str(e)))
        except httpx.HTTPError as e:
            self.results.append((name, False, f"HTTP error: {e}"))

    def phase0(self) -> None:
        def health() -> str:
            r = self.c.get(f"{API}/health")
            assert r.status_code == 200, f"status {r.status_code}"
            h = r.json()
            assert h["ollama"] == "up", "Ollama is down"
            assert h["models_ready"], f"missing models: {h['missing_models']}"
            return f"ollama up, models ready, v{h['version']}"

        def info() -> str:
            r = self.c.get(f"{API}/system/info")
            assert r.status_code == 200, f"status {r.status_code}: {r.text[:200]}"
            i = r.json()
            assert i["model"]["digest"], "model digest missing (model not pulled?)"
            return (
                f"{i['model']['name']} {i['model']['quantization']} digest={i['model']['digest'][:12]} gpu={i['gpu']}"
            )

        def contract() -> str:
            spec = self.c.get(f"{API}/openapi.json").json()
            missing = [p for p in PLANNED_PATHS if API + p not in spec["paths"]]
            assert not missing, f"missing paths: {missing}"
            return f"{len(spec['paths'])} paths in contract"

        def problem_json() -> str:
            r = self.c.get(f"{API}/documents/does-not-exist")
            assert r.headers["content-type"].startswith("application/problem+json"), r.headers["content-type"]
            body = r.json()
            assert {"type", "title", "status", "code"} <= body.keys(), body
            return f"{r.status_code} {body['code']}"

        def loopback_only() -> str:
            host = httpx.URL(str(self.c.base_url)).host
            assert host in ("127.0.0.1", "localhost", "::1"), f"API is not on loopback: {host}"
            return host

        for name, fn in [
            ("health", health),
            ("system/info", info),
            ("contract paths", contract),
            ("problem+json errors", problem_json),
            ("loopback bind", loopback_only),
        ]:
            self.check(f"P0 {name}", fn)

    def phase1(self) -> None:
        """Synthetic fixtures only (tests/fixtures). Never upload a real document here."""
        fixtures = Path(__file__).resolve().parents[1] / "tests" / "fixtures"
        uploaded: list[dict] = []

        def upload(name: str, mime: str) -> httpx.Response:
            return self.c.post(f"{API}/documents", files={"file": (name, (fixtures / name).read_bytes(), mime)})

        def upload_and_check_offsets() -> str:
            r = upload("in_rental_missing_clauses.pdf", "application/pdf")
            assert r.status_code == 201, f"status {r.status_code}: {r.text[:200]}"
            s = r.json()
            assert s["quick_detect"] == {"doc_type": "rental", "country": "IN"}, s["quick_detect"]
            d = self.c.get(f"{API}/documents/{s['document_id']}").json()
            page_text = "\n\n".join(p["text"] for p in d["pages"])
            for c in d["clauses"]:
                assert page_text[c["char_start"] : c["char_end"]] == c["text"], f"offset mismatch {c['id']}"
            uploaded.append(s)
            return f"{len(d['clauses'])} clauses, every offset round-trips"

        def injection_is_flagged_and_removed() -> str:
            r = upload("adv_white_text_injection.pdf", "application/pdf")
            assert r.status_code == 201, f"status {r.status_code}"
            s = r.json()
            assert any(w["code"] == "HIDDEN_CONTENT_FOUND" for w in s["warnings"]), "no hidden-content warning"
            d = self.c.get(f"{API}/documents/{s['document_id']}").json()
            text = " ".join(c["text"] for c in d["clauses"])
            assert "Ignore previous instructions" not in text, "injected text reached the clauses"
            uploaded.append(s)
            return f"{len(s['hidden_findings'])} hidden finding(s), injected text absent from clauses"

        def failure_codes() -> str:
            expected = {
                "encrypted.pdf": ("application/pdf", 422, "ENCRYPTED_PDF"),
                "corrupt.pdf": ("application/pdf", 422, "MALFORMED_FILE"),
                "scanned_page.pdf": ("application/pdf", 422, "SCANNED_NO_TEXT"),
                "empty.txt": ("text/plain", 422, "EMPTY_DOCUMENT"),
            }
            for name, (mime, status, code) in expected.items():
                r = upload(name, mime)
                assert r.status_code == status and r.json()["code"] == code, f"{name}: {r.status_code} {r.text[:120]}"
            return ", ".join(code for _, _, code in expected.values())

        def delete_shreds() -> str:
            assert uploaded, "no document to delete"
            doc_id = uploaded[0]["document_id"]
            assert self.c.delete(f"{API}/documents/{doc_id}").json() == {"deleted": True, "crypto_shredded": True}
            assert self.c.get(f"{API}/documents/{doc_id}").status_code == 404, "document still readable"
            return "deleted, then 404"

        def privacy() -> str:
            st = self.c.get(f"{API}/privacy/status").json()
            assert st["egress_guard"]["active"] is True, "egress guard is not active"
            return f"egress guard active, blocked_attempts={st['egress_guard']['blocked_attempts']}"

        for name, fn in [
            ("upload + offsets", upload_and_check_offsets),
            ("hidden injection", injection_is_flagged_and_removed),
            ("failure codes", failure_codes),
            ("crypto-shred delete", delete_shreds),
            ("privacy status", privacy),
        ]:
            self.check(f"P1 {name}", fn)

        def temp_files() -> str:
            before = self.temp_files()
            upload("in_rental_11m_leave_license.txt", "text/plain")
            written = self.temp_files() - before
            assert written == 0, f"{written} temp file write(s) during upload"
            return "0 temp files written"

        self.check("P1 temp files during upload", temp_files)

    def temp_files(self) -> int:
        return int(self.c.get(f"{API}/privacy/status").json()["temp_files_created"])


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--phase", default="0", help="0..5 or 'all' (cumulative)")
    ap.add_argument("--base", default="http://127.0.0.1:8000")
    args = ap.parse_args()
    s = Smoke(args.base)
    upto = 5 if args.phase == "all" else int(args.phase)
    for n in range(upto + 1):
        fn = getattr(s, f"phase{n}", None)
        if fn is None:
            print(f"(phase {n} smoke checks not written yet)")
            continue
        fn()
    width = max(len(n) for n, _, _ in s.results)
    for name, ok, msg in s.results:
        print(f"{'PASS' if ok else 'FAIL'}  {name:<{width}}  {msg}")
    failed = sum(not ok for _, ok, _ in s.results)
    print(f"\n{len(s.results) - failed}/{len(s.results)} checks passed")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
