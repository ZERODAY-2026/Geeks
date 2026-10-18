# LexiShield

**Private, on-device legal document triage, powered by Google Gemma.**
ZeroDay OSS Hacktoberfest 2026 · IIIT Dharwad · Track PS2 (Private Legal Document Triage Agent)

LexiShield reads a rental agreement, employment contract, freelance agreement or legal notice **on your own
machine**. It explains the important clauses in plain language, says clearly when the document is **silent**,
cites the exact passage behind every statement, refuses to give legal verdicts, and points you to the right
kind of professional. No document content leaves the device.

> LexiShield gives preliminary information to help you understand a document. It is **not legal advice** and
> cannot decide whether anything is legal or enforceable.

## Status

| Phase | Scope | Status |
|---|---|---|
| P0 | Foundations, LLM gateway, benchmarks, frozen API contract | ✅ in progress / see `backend/eval/results` |
| P1 | Ingestion, trust boundary, retrieval | ⏳ |
| P2 | Checklist, cards, verification gate, jobs + SSE | ⏳ |
| P3 | Ask agent, scenarios, statute context, escalation brief | ⏳ |
| P4 | Air-gap proof, signed receipts, red team, CUAD eval | ⏳ |
| P5 | Freeze, docs, clean-clone reproduction | ⏳ |

The full build plan (architecture, phases, test gates) is in [`docs/plan/LexiShield_Build_Plan.docx`](docs/plan/LexiShield_Build_Plan.docx).

## Repository layout

```
backend/     Python 3.12 FastAPI service (uv project): src/lexishield, tests, scripts, config, packs
contracts/   Frozen API contract for the frontend: openapi.json + examples/*.json
frontend/    React UI (built separately against contracts/)
docs/        Build plan, architecture figures, privacy and model docs
```

## Quick start

### 1. Prerequisites (set-up time, the only time network is needed)

- [uv](https://docs.astral.sh/uv/) (it installs Python 3.12 automatically)
- [Ollama](https://ollama.com) **0.40+**
- Models (pick the profile for your machine):

| Profile | Machine | Chat model | Embeddings |
|---|---|---|---|
| `gpu` (default) | NVIDIA GPU with 8 GB+ VRAM (team: RTX 5070 laptop) | `gemma4:e4b-it-qat` (6.1 GB) | `embeddinggemma:300m` |
| `cpu` | CPU-only laptop, 12 GB+ RAM | `gemma4:e2b-it-qat` (4.3 GB) | `embeddinggemma:300m` |

```bash
ollama pull gemma4:e4b-it-qat      # gpu profile   (cpu profile: gemma4:e2b-it-qat)
ollama pull embeddinggemma:300m
```

### 2. Install and run the backend

**Linux / macOS**
```bash
cd backend
uv sync --frozen
uv run lexishield info --profile cpu        # shows the models Ollama has
uv run lexishield serve --profile cpu       # API on http://127.0.0.1:8000  (docs at /docs)
```

**Windows (PowerShell)**
```powershell
cd backend
uv sync --frozen
uv run lexishield serve                     # gpu profile (default)
```
On Windows, quit the Ollama tray app during demos and run `ollama serve` in a terminal, so the
desktop app's background update check is not running. Document processing never uses the network.

### 3. Run the tests (phase gates)

```bash
cd backend
uv run pytest -m phase0 -q                                  # unit + contract tests (no model needed)
LEXISHIELD_MODELS__PROFILE=cpu uv run pytest -m live -q     # live Gemma checks (model must be pulled)
uv run python scripts/bench.py --label <machine> --trials 10   # speed / memory benchmark
uv run python scripts/smoke_api.py --phase 0                # against a running server
```

On Windows PowerShell, set the profile with `$env:LEXISHIELD_MODELS__PROFILE="cpu"` instead.

## Configuration

`backend/config/lexishield.yaml` holds every setting: models, limits, feature flags and retention TTL. Override any
value with `LEXISHIELD_<SECTION>__<KEY>`, e.g. `LEXISHIELD_MODELS__PROFILE=cpu` or
`LEXISHIELD_OLLAMA__HOST=http://127.0.0.1:11434`. The server refuses to bind a non-loopback address.

## For the frontend team

Build against [`contracts/`](contracts/README.md). It holds the OpenAPI spec and example payloads for every
response. Endpoints that are not built yet return `501 NOT_IMPLEMENTED` (problem+json) naming the phase
that delivers them.

## Licence and attributions

Code: Apache-2.0 (see [LICENSE](LICENSE)). Model and dataset terms: see [NOTICE](NOTICE).
