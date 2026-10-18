"""Fail if the locked dependency tree contains telemetry, analytics or crash-reporting packages.

Reads uv.lock (the exact versions that run), so transitive dependencies are included.
`opentelemetry-api` is allowed: FastAPI depends on it, and it exports nothing without an SDK or exporter.

Usage:  uv run python scripts/audit_deps.py        (exit 0 = clean, 1 = a banned package is locked)
"""

from __future__ import annotations

import sys
import tomllib
from pathlib import Path

LOCK = Path(__file__).resolve().parents[1] / "uv.lock"

# Exact names, or prefixes ending in "-" (a family such as opentelemetry-exporter-otlp-proto-http).
BANNED_EXACT = frozenset(
    {
        "sentry-sdk",
        "posthog",
        "mixpanel",
        "analytics-python",
        "amplitude-analytics",
        "datadog",
        "ddtrace",
        "rollbar",
        "bugsnag",
        "wandb",
        "newrelic",
        "streamlit",
        "logfire",
        "langsmith",
        "appinsights",
        "google-analytics-data",
    }
)
BANNED_PREFIXES = ("opentelemetry-sdk", "opentelemetry-exporter-", "sentry-")


def locked_packages(lock: Path) -> list[str]:
    data = tomllib.loads(lock.read_text(encoding="utf-8"))
    return sorted({p["name"].lower() for p in data.get("package", [])})


def banned(name: str) -> bool:
    return name in BANNED_EXACT or name.startswith(BANNED_PREFIXES)


def main() -> int:
    names = locked_packages(LOCK)
    hits = [n for n in names if banned(n)]
    print(f"checked {len(names)} locked packages in {LOCK.name}")
    for n in hits:
        print(f"BANNED: {n}")
    print("audit: FAIL" if hits else "audit: PASS (no telemetry, analytics or crash-reporting packages)")
    return 1 if hits else 0


if __name__ == "__main__":
    sys.exit(main())
