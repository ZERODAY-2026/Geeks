"""Phase 0 gate: settings, system endpoints, error contract, frozen OpenAPI + examples."""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

from conftest import FakeOllama, make_client
from lexishield.settings import BACKEND_DIR, Settings

pytestmark = pytest.mark.phase0

API = "/api/v1"


# ---------------------------------------------------------------- settings


def test_yaml_config_loads_profiles() -> None:
    s = Settings()
    assert s.server.host == "127.0.0.1"
    assert s.models.gpu.chat == "gemma4:e4b-it-qat"
    assert s.models.cpu.chat == "gemma4:e2b-it-qat"
    assert s.models.options.temperature == 0


def test_env_overrides_yaml(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("LEXISHIELD_MODELS__PROFILE", "cpu")
    monkeypatch.setenv("LEXISHIELD_OLLAMA__HOST", "http://127.0.0.1:9999")
    s = Settings()
    assert s.models.active.chat == "gemma4:e2b-it-qat"
    assert s.ollama.host == "http://127.0.0.1:9999"


# ---------------------------------------------------------------- system endpoints


def test_health_up_and_ready(client) -> None:
    r = client.get(f"{API}/health")
    assert r.status_code == 200
    assert r.json() == {"status": "ok", "ollama": "up", "models_ready": True, "missing_models": [], "version": "0.1.0"}


def test_health_reports_missing_model(settings) -> None:
    fake = FakeOllama(models=[{"model": "embeddinggemma:300m", "digest": "sha256:b", "details": {}}])
    with make_client(settings, fake) as c:
        h = c.get(f"{API}/health").json()
    assert h["ollama"] == "up" and h["models_ready"] is False
    assert h["missing_models"] == ["gemma4:e4b-it-qat"]


def test_health_when_ollama_down(settings) -> None:
    with make_client(settings, FakeOllama(down=True)) as c:
        r = c.get(f"{API}/health")
    assert r.status_code == 200
    assert r.json()["ollama"] == "down" and r.json()["models_ready"] is False


def test_system_info_reports_digest_and_quantization(client) -> None:
    i = client.get(f"{API}/system/info").json()
    assert i["model"]["name"] == "gemma4:e4b-it-qat"
    assert i["model"]["digest"] == "sha256:aaa"
    assert i["model"]["quantization"] == "Q4_0"
    assert i["embed_model"]["name"] == "embeddinggemma:300m"
    assert i["agent_mode"] == "tools"


def test_system_info_503_problem_when_ollama_down(settings) -> None:
    with make_client(settings, FakeOllama(down=True)) as c:
        r = c.get(f"{API}/system/info")
    assert r.status_code == 503
    assert r.headers["content-type"].startswith("application/problem+json")
    assert r.json()["code"] == "MODEL_UNAVAILABLE"


def test_benchmark_404_then_served(client, settings) -> None:
    assert client.get(f"{API}/system/benchmark").json()["code"] == "NO_BENCHMARK"
    results = settings.paths.resolve("results_dir")
    results.mkdir(parents=True)
    (results / "bench_x_test.json").write_text(
        json.dumps(
            {
                "model": "m",
                "label": "test",
                "trials": 2,
                "schema_valid": 2,
                "schema_valid_rate": 1.0,
                "created_at": "2026-10-18T12:00:00Z",
            }
        )
    )
    r = client.get(f"{API}/system/benchmark")
    assert r.status_code == 200 and r.json()[0]["schema_valid_rate"] == 1.0


# ---------------------------------------------------------------- error contract


@pytest.mark.parametrize(
    ("method", "path", "status", "code"),
    [
        ("get", "/api/v1/nope", 404, "NOT_FOUND"),
        ("get", "/api/v1/eval/summary", 501, "NOT_IMPLEMENTED"),  # Phase 4; packs are built in Phase 2
        ("post", "/api/v1/documents/abc/ask", 422, "VALIDATION_ERROR"),
        ("delete", "/api/v1/health", 405, "METHOD_NOT_ALLOWED"),
    ],
)
def test_errors_are_problem_json(client, method, path, status, code) -> None:
    r = getattr(client, method)(path)
    assert r.status_code == status
    assert r.headers["content-type"].startswith("application/problem+json")
    body = r.json()
    assert body["code"] == code and body["status"] == status and body["type"].startswith("https://lexishield.local/")


def test_cors_allows_only_configured_local_origins(client) -> None:
    ok = client.options(
        f"{API}/health", headers={"Origin": "http://localhost:5173", "Access-Control-Request-Method": "GET"}
    )
    bad = client.options(
        f"{API}/health", headers={"Origin": "https://evil.example", "Access-Control-Request-Method": "GET"}
    )
    assert ok.headers.get("access-control-allow-origin") == "http://localhost:5173"
    assert "access-control-allow-origin" not in bad.headers


def test_cli_refuses_non_loopback_bind() -> None:
    r = subprocess.run(
        [sys.executable, "-m", "lexishield.cli", "serve", "--host", "0.0.0.0"],
        capture_output=True,
        text=True,
        timeout=30,
        env={**os.environ},
    )
    assert r.returncode != 0 and "non-loopback" in r.stderr


# ---------------------------------------------------------------- frozen contract


def test_openapi_contains_every_planned_path(client) -> None:
    from smoke_api import PLANNED_PATHS

    spec = client.get(f"{API}/openapi.json").json()
    missing = [p for p in PLANNED_PATHS if API + p not in spec["paths"]]
    assert not missing


def test_contract_files_are_up_to_date() -> None:
    """contracts/ must be regenerated (scripts/export_openapi.py) whenever models or routes change."""
    r = subprocess.run(
        [sys.executable, str(BACKEND_DIR / "scripts" / "export_openapi.py"), "--check"],
        capture_output=True,
        text=True,
        timeout=60,
    )
    assert r.returncode == 0, f"stale contract files, run export_openapi.py:\n{r.stdout}{r.stderr}"


def test_examples_validate_against_models() -> None:
    from contract_examples import EXAMPLE_MODELS

    ex_dir = BACKEND_DIR.parent / "contracts" / "examples"
    for name, model in EXAMPLE_MODELS.items():
        data = json.loads((ex_dir / f"{name}.json").read_text(encoding="utf-8"))
        for item in data if isinstance(data, list) else [data]:
            model.model_validate(item)


def test_example_citations_point_at_their_quotes() -> None:
    """Invariant preview: a citation's quote is exactly the page text at its offsets."""
    from contract_examples import DETAIL, REPORT

    page = DETAIL.pages[0]
    for card in REPORT.cards:
        c = card.source
        if c.page == page.page:
            assert page.text[c.char_start - page.char_start : c.char_end - page.char_start] == c.quote
    for clause in DETAIL.clauses:
        assert page.text[clause.char_start - page.char_start : clause.char_end - page.char_start] == clause.text


def test_no_secrets_in_backend_sources() -> None:
    import re

    pat = re.compile(r"(api[_-]?key|secret|token)\s*[:=]\s*['\"][A-Za-z0-9_\-]{16,}", re.I)
    hits = [
        p
        for p in Path(BACKEND_DIR).rglob("*.py")
        if ".venv" not in p.parts and pat.search(p.read_text(encoding="utf-8"))
    ]
    assert not hits
