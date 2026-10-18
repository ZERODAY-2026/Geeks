# LexiShield: implementation plan, setup and phase tests

Track PS2 (ZeroDay OSS Hacktoberfest 2026). Backend first, then the frontend, which is built separately against
`contracts/`. The full design (architecture, rationale, risk register) is in
[`docs/plan/LexiShield_Build_Plan.docx`](plan/LexiShield_Build_Plan.docx). This file is the working checklist.
Status and decisions: [`PROJECT_LOG.md`](PROJECT_LOG.md).

---

## 1. Setup (once per machine)

Run from the repo root unless a step says otherwise.

### 1.1 Tools
| Tool | Linux (Ryzen laptop) | Windows (HP OMEN) |
|---|---|---|
| uv | `curl -LsSf https://astral.sh/uv/install.sh \| sh` | `powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 \| iex"` |
| Ollama 0.40+ | https://ollama.com/download | https://ollama.com/download |
| Git | yes | yes |

Python 3.12 is installed automatically by uv.

### 1.2 Models (set-up time only, network allowed)
```bash
ollama pull embeddinggemma:300m
ollama pull gemma4:e2b-it-qat        # CPU profile (4.3 GB)
ollama pull gemma4:e4b-it-qat        # GPU profile (6.1 GB), needs 8 GB VRAM
ollama pull gemma3n:e4b              # optional comparison row for the benchmark
```

### 1.3 Backend
```bash
cd backend
uv sync --frozen
uv run lexishield info --profile cpu     # lists the models Ollama has
```

### 1.4 Run the API (loopback only)
```bash
uv run lexishield serve --profile cpu    # http://127.0.0.1:8000  (docs: /docs)
```
Use `--profile gpu` on the OMEN. The server refuses non-loopback addresses on purpose.

### 1.5 Windows notes (OMEN)
- Quit the Ollama tray app during demos and run `ollama serve` in a terminal instead.
- `set LEXISHIELD_MODELS__PROFILE=cpu` becomes `$env:LEXISHIELD_MODELS__PROFILE="cpu"` in PowerShell.
- Full runbook: [`docs/omen-setup.md`](omen-setup.md).

### 1.6 Configuration
`backend/config/lexishield.yaml` holds every setting. Override any value with `LEXISHIELD_<SECTION>__<KEY>`,
for example `LEXISHIELD_MODELS__OPTIONS__THINK=true`. Model names live in config, not code.

---

## 2. Repository map

```
backend/
  config/lexishield.yaml       settings (models, limits, privacy, flags)
  src/lexishield/
    api/                       FastAPI app, problem+json errors, routers (system, documents, analysis, interaction, meta)
    llm/gateway.py             the ONLY module that calls Gemma (schema enforcement, one repair, timeouts)
    models/                    domain.py (core objects) and api.py (request/response contract)
    settings.py  cli.py
  scripts/                     bench.py, smoke_api.py, export_openapi.py, contract_examples.py
  tests/                       conftest.py (fake Ollama, test double only), test_phase0_*.py
contracts/                     openapi.json + examples/*.json (frozen contract for the frontend)
docs/                          this file, PROJECT_LOG.md, omen-setup.md, plan/, figures/
frontend/                      React app (separate build)
```

---

## 3. Phase plan and run-test gates

Every gate runs cumulatively: a later phase also re-runs the earlier phases' tests. Gate command pattern:
`uv run pytest -m "phase0 or phase1 ..."`.

### Phase 0: foundations and frozen contract (planned 0:00–0:45)
**Done:** project scaffold, typed settings, domain and API models, LLM gateway, system endpoints
(health, system/info, benchmark), problem+json errors, 501 stubs for every planned endpoint, OpenAPI export and
example payloads, CLI, benchmark script, smoke script, 26 tests.

**Gate tests (run these; paste output in the team channel):**
```bash
cd backend
uv run ruff check src scripts tests                                 # lint
uv run pytest -m phase0 -q                                          # 26 tests incl. live Gemma (needs Ollama + model)
uv run python scripts/export_openapi.py --check                     # contract not stale (exit 0)
uv run lexishield serve --profile cpu &                             # then in another terminal:
uv run python scripts/smoke_api.py --phase 0                        # 5 live API checks
```
**Benchmark (required for the memory and speed report; run on each machine):**
```bash
uv run python scripts/bench.py --models gemma4:e2b-it-qat --label ryzen7-7730u-cpu --trials 10
uv run python scripts/bench.py --models gemma4:e4b-it-qat gemma3n:e4b --label omen-rtx5070 --trials 10
```
Commit the resulting `backend/eval/results/bench_*.json` files for each machine.

**Pass criteria:** the phase0 tests are green; the smoke checks pass; a benchmark exists for each machine; the
primary model is chosen with its measured status-correct rate (see Open issues in the log).

### Phase 1: ingestion, trust boundary, retrieval (planned 0:45–2:15)
**Status:** not started. Stub endpoints exist; the phase1 tests are not written yet.

**Tests to write (`tests/test_phase1_*.py`, marker `phase1`):**
- Offset round-trip: `doc.text[c.char_start:c.char_end] == clause.text` for every clause in each fixture.
- Hidden-content detector: white text, zero-width and bidi characters each produce a HIGH finding; the
  injected text is absent from prompt payloads.
- Failure codes: encrypted, corrupt, empty and scanned PDFs return 422 with their specific codes.
- Egress guard: a connection to `example.com:443` raises `EgressBlocked` and the counter increments;
  loopback to Ollama still works.
- Temp-file sentinel: no temp files created during upload and ingest.
- Vault: data is unreadable after `DELETE /documents/{id}`.
- Retrieval recall@6 ≥ 0.9 on 15 hand-labelled queries; classifier correct on 5 of 5 core fixtures.

**Gate command:** `uv run pytest -m "phase0 or phase1" -q`

### Phase 2: analysis core (planned 2:15–3:45)
**Tests to write (marker `phase2`):**
- Quote verifier and distortion checker unit tests (about 40 cases), including: ₹1,50,000 vs ₹15,000,
  30 vs 60 days, and "shall not" vs "shall" must all be caught.
- Silence double-key: NOT_MENTIONED is kept only when the lexicon also finds nothing.
- Invariant: zero unverified quotes in any API output across all fixtures (hard fail).
- Golden documents: topic status matches the answer key on at least 80% of topics; every silence in the key
  is reported as NOT_MENTIONED or UNCLEAR, never ENTAILED.
- SSE events arrive in order: classification.ready → checklist.item / card.ready → report.ready.
- Median card reading grade ≤ 9.

**Gate command:** `uv run pytest -m "phase0 or phase1 or phase2" -q`
**Smoke:** `uv run python scripts/smoke_api.py --phase 2`

### Phase 3: interaction layer (planned 3:45–5:00)
**Tests to write (marker `phase3`):**
- Verdict questions ("is this enforceable?", "should I sign?") return LEGAL_VERDICT_DECLINED with escalation,
  in 100% of red-team variants.
- Questions the document does not answer return NOT_IN_DOCUMENT in at least 90% of cases, with no fabricated citation.
- Every ANSWERED claim has at least one verified citation; output-guard hits in final answers = 0.
- A scenario with a missing input returns `computable: false`, never a guessed number.
- `/statutes` shows section status and the snapshot tag; with no index it returns `available: false`.

**Gate command:** `uv run pytest -m "phase0 or phase1 or phase2 or phase3" -q`

### Phase 4: proof and robustness (planned 5:00–6:15)
**Tests to write (marker `phase4`, `tests/redteam/`):**
- Red-team suite of at least 25 cases (injection, conflicting clauses, malformed files, verdict bait, long
  documents). Target pass rate ≥ 90%; every failure is listed in `docs/results.md`.
- Receipt signature verifies; model digest matches `ollama show`.
- Air-gap run: the full analysis plus five questions succeed with `non_loopback_connects: 0`.
- CUAD evaluation runs end to end on 20 contracts.

**Commands:**
```bash
uv run pytest -q
docker compose -f deploy/compose.airgap.yml run --rm prover
uv run python scripts/verify_receipt.py eval/results/receipts/latest.json
uv run python scripts/eval_cuad.py --n 20 --out eval/results/
```

### Phase 5: freeze, integrate, reproduce (planned 6:15–7:30)
**Tests:** a fresh clone on a second machine runs `uv sync --frozen`, the server, and
`smoke_api.py --phase all` using only README steps. Then the secret scan (no keys in the repo) and the
licence and NOTICE check.

```bash
git clone <repo> && cd Geeks/backend && uv sync --frozen
uv run lexishield serve --profile cpu &
uv run python scripts/smoke_api.py --phase all
```

### Phase 6: demo and submission (planned 7:30–8:00)
Record the demo with Wi-Fi off and connection monitoring visible. Final green run:
`uv run pytest -q && uv run python scripts/smoke_api.py --phase all`. Tag `v1.0`.

---

## 4. Rules that apply to every phase
- No network call may carry document content. The only model client is `llm/gateway.py`.
- Never display a quote that the verifier did not match to the source text.
- Never add a telemetry or analytics dependency. `scripts/audit_deps.py` (Phase 1) enforces this.
- Contract changes after Phase 0 are additive only. Run `scripts/export_openapi.py` after any model or route change.
- Do not commit `backend/data/`, `.venv/`, secrets or downloaded models.
