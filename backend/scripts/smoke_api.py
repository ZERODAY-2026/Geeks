"""Smoke-test a RUNNING LexiShield API, phase by phase (part of each run-test gate).

Usage:
  uv run lexishield serve --profile cpu        # in another terminal
  uv run python scripts/smoke_api.py --phase 0 [--base http://127.0.0.1:8000]
"""

from __future__ import annotations

import argparse
import sys
from collections.abc import Callable

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
