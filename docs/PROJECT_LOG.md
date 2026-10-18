# LexiShield: project log (status, decisions, findings)

Last updated: 2026-10-18 (Phase 0). Update this file at the end of each phase.

## 1. Status

| Phase | State | Evidence |
|---|---|---|
| P0 Foundations and contract | **Code complete, gate partly passed.** Pytest 26/26 green on the Ryzen laptop. Clean benchmark runs on both machines are still to do. The primary model's accuracy is an open issue (section 4). | `backend/tests/test_phase0_*.py`, `contracts/` |
| P1 Ingestion, trust, retrieval | Not started | stubs return 501 |
| P2–P6 | Not started | |

**Is Phase 0 done?** Mostly. What is green: the scaffold, settings, models, gateway, API skeleton, contract
export, error contract, and the live check that Gemma returns schema-valid JSON. What is not yet done: the OMEN
benchmark, the decision on the primary model (see section 4), and the team's own run of the gate.

## 2. What has worked
- **Gemma 4 E2B (`gemma4:e2b-it-qat`) on the Ryzen 7 7730U CPU** returns schema-valid JSON 10/10 times at
  temperature 0 with Ollama's JSON-schema `format`. Measured speed: about 16 tokens/s generation, about 13.6 s
  per structured call (synthetic clause, 800 output tokens).
- **Turning off thinking** (`think: false`) cut latency about 3× (16 s vs 44 s per call) with the same output
  length. Now the default in `config/lexishield.yaml`.
- **Ollama 0.40.6** serves both models; the API reports digests and quantization from `/api/tags`.
- **FastAPI + Pydantic** contract: `contracts/openapi.json` and 21 example payloads are generated from the real
  models. A test fails if they go stale.
- **problem+json errors** for every failure, including Starlette's own 404/405.
- **Loopback-only** bind is enforced in code (`lexishield serve` refuses other addresses).

## 3. What did not work (and the fixes)
| Problem | Cause | Fix |
|---|---|---|
| Live test failed with "Event loop is closed" | The Ollama async client was created in one `asyncio.run` and reused in another | The test now creates the gateway inside the same loop |
| 404/405 responses were not problem+json | Starlette raises its own `HTTPException`, which bypasses FastAPI's handler | Handler registered for `starlette.exceptions.HTTPException` |
| Benchmark reported RAM 26 MB | The memory sampler looked for `ollama` processes only; Ollama 0.40 runs the model in a `llama-server` child process | Sampler matches `llama-server` too, and reads Ollama's `/api/ps` for model size and VRAM share |
| `uv add` timed out (120 s) while the model downloaded | Shared bandwidth | Ran in the background |
| Ruff reported 10 issues after the first write | Long lines and import order in generated code | `ruff check --fix` and `ruff format` |

## 4. Open issues (must be resolved before Phase 2)
1. **Accuracy is not yet proven.** The benchmark passed the gate because the output was valid JSON. But for a
   synthetic deposit clause that clearly states the amount and refund rule, the model returned
   `NOT_MENTIONED` in 10 of 10 trials. Schema validity is not correctness. The Phase 0 gate needs an
   accuracy check: the `bench.py` script now also reports `status_correct_rate` and `quote_verbatim_rate`
   (the earlier run predates this and does not have them). Compare `gemma4:e4b-it-qat` and `gemma3n:e4b`
   on the OMEN and pick the model on that number.
2. **The Ryzen benchmark JSON was removed** because its RAM figure was wrong (see section 3). A clean run is
   needed for the record; the tok/s numbers from that run are still in this log.
3. **The OMEN benchmark has not been run.** The `gpu` profile (`gemma4:e4b-it-qat`) is untested.
4. **The contract's example `benchmark.json` uses placeholder numbers.** Replace them with real results.
5. **`scripts/audit_deps.py`, `scripts/verify_receipt.py` and `scripts/eval_cuad.py`** are referenced in the plan
   but not written yet (Phases 1 and 4).

## 5. Decisions made in chat (and why)
| Decision | Why |
|---|---|
| **PS2 track, product LexiShield**, scope = India rental + employment (deep), freelance MSA + legal notices (standard) | Best fit for the rubric and the India datasets; honest scoping is rewarded |
| **Backend first**, FastAPI, with a React frontend built separately (Antigravity) | The team split: three people on the backend, one on the frontend |
| **Primary model `gemma4:e4b-it-qat`** on the OMEN; **`gemma4:e2b-it-qat`** on CPU laptops | Fits 8 GB VRAM; runs on 13 GB laptops; both are Gemma 4 edge models (accepted by PS2) |
| **No hardware TEE** | Not available on the team's machines (SGX deprecated on client Core, TDX/SEV are server-only, NVIDIA GPU TEE is data-centre only). We implement isolate, seal and attest in software and say so |
| **Distortion check** (numbers, negations and roles must match the cited source) as the winning edge | Targets rubric criterion 1 and the misgrounding risk directly; cheap to build |
| **Thinking off** for Gemma 4 | About 3× faster with the same output |
| **Nothing from the model reaches the user without a verified source span** | Core rubric rule (grounding, criterion 2) |
| **Remote branch `phase0/scaffold`** for the first push | Team can pull and test without touching `main` yet |

## 6. Team setup notes
- Windows (OMEN): `docs/omen-setup.md`. Run the benchmark there and commit the JSON.
- Ryzen laptop: CPU profile; development only with synthetic documents.
- No real documents go into the repo or into any benchmark at any stage.
