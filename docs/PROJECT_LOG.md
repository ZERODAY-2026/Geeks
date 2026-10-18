# LexiShield: project log (status, decisions, findings)

Last updated: 2026-10-18 (Phase 0). Update this file at the end of each phase.

## 1. Status

| Phase | State | Evidence |
|---|---|---|
| P0 Foundations and contract | **Code complete, gate partly passed.** Pytest 26/26 green on the Ryzen laptop. Clean benchmark runs on both machines are still to do. The primary model's accuracy is an open issue (section 4). | `backend/tests/test_phase0_*.py`, `contracts/` |
| P1 Ingestion, trust, retrieval | **Gate passed on the OMEN** (`pytest -m "phase0 or phase1"`: 71 passed; smoke `--phase 1`: 11/11). Built: PDF, DOCX and TXT ingestion with exact offsets; visible-text-only clauses; hidden-text and injection detection; flagged text removed before any prompt; temp-file sentinel (0 writes during upload); early 413 by Content-Length; AES-GCM crypto-shred vault; egress guard; BM25 + EmbeddingGemma hybrid retrieval with RRF and cross-reference expansion; Gemma classifier with signals fallback; synthetic fixtures and answer keys (`scripts/make_fixtures.py`); `scripts/audit_deps.py`. Not built: `trust/redact_log.py`, separate `layout.py`/`normalize.py`/`xref.py`/`injection.py` modules (their logic lives in `pipeline.py`, `hidden.py`, `segment.py`, `prompt_view.py`), OCR. | `backend/tests/test_phase1_*.py` |
| P2 Analysis core | **Gate passed on the OMEN** (`pytest -m "phase0 or phase1 or phase2"`: 151 passed; smoke `--phase 2`: 14/14 including a live analysis). Built: quote verifier (exact, normalized, fuzzy ≥ 92 with number and negation checks), facts extractor, distortion checker (facts FAIL, negation and party-role WARN), silence double-key, tiers, advice guard, YAML packs (in_rental and in_employment at 18 topics, msa_generic and notice_generic), escalation routes, checklist agent, card writer with textstat reading grade, orchestrator, one-GPU-worker job queue, SSE stream, report sealed in the vault. Golden keys in `tests/fixtures/golden_keys.json`, written before the first run. Last golden run: rental 97% (35/36), employment 94% (17/18), median reading grade 7.8 over 22 cards. Caveats: the prompt was changed four times after golden failures (label definitions, explicit evidence and explanation, required schema fields, reading level); the keys were not changed, but the golden set is also the tuning set, so it is not a held-out test. Model output varies between runs; one run had a different rental miss. Hardening round: job events are now sealed in the vault (shredded with the document); cancel is tested while running and while queued; severity rules come from the pack data; distortion warns only on modal negation; amounts written in words are facts; jurisdiction comes from the governing-law clause, with a citation. Held-out check (keys written before any run, prompts not tuned on them): rental 18/18, employment 16/18 (89%), notice 10/10 then 9/10 on a second run, MSA 10/12 (83%). The held-out documents have now been run twice, so they are no longer pristine. Fresh check (new documents, keys written first, three runs each, no changes after the run): rental 89/94/94% with one silence reported as ENTAILED (subletting: the occupancy clause was read as a subletting rule, quote verified but the claim over-reaches the topic); employment 72/72/72%, the model missed 'trial period' as probation and gave UNCLEAR on termination, IP and overtime; notice 80/80/80%, at the threshold. Phase 2 does not yet pass on fresh documents. Next step is a deliberate fix round, followed by a new fresh set. Grounding gate (relevance gate, default on): a verified quote must use the topic's own lexicon terms to support it. CUAD evaluation (15 public contracts, 6 MSA topics mapped from CUAD categories, 90 checks, local only, not committed): gate off -> over-claims 3, false silences 1, detections 18 of 41; gate on -> over-claims 2, false silences 1, detections 16 of 41. Two of the three baseline over-claims are CUAD label gaps: both contracts contain IP ownership clauses that CUAD did not annotate. The gate's cost is lexicon coverage: 'governed and construed under' and 'first six (6) months' were rejected although they state the topic. Golden with the gate on: rental 35/36, employment 16/18, all six golden tests still pass. The lexicon test was then replaced by a per-quote model relevance check, and every pack hypothesis was rewritten to a single claim (the employment misses came from two-part questions such as 'how long probation lasts and what happens at its end'). Third fresh set (keys written first, three runs each): rental 100/100/100%, employment 94/94/94%, notice 90/90/90%, no silence reported as ENTAILED (occupancy-vs-subletting and bond-vs-bonus traps held). Gate: 183 passed. Earlier fresh sets moved to the 'history' marker (scored against the old two-part questions); for the record they now give employment 89% and 94-100% (were 72%), rental 94%, notice 70-80% and 90%. Known gap: notice response deadlines phrased as 'pay within N days' often come back UNCLEAR. CUAD with the model check: termination dropped from the mapping (CUAD labels only termination for convenience); on the remaining topics the two over-claims are the known IP label gaps. Report examples are captured from a real run (scripts/capture_examples.py). | `backend/tests/test_phase2_*.py`, `backend/packs/`, `backend/escalation/` |
| P3 Interaction layer | **Built, not yet tested** (branch `phase3/interaction`; no test, evaluation or server run, by request). Built: rule-based intent router (verdicts declined before any model call); Ask in pipeline mode with the same gate as the checklist (quote verifier, per-quote relevance check, distortion checker, output guard with one regeneration); NOT_IN_DOCUMENT when no claim survives; what-if scenarios as YAML plus an engine that adds up only verified amounts (rental early exit, deposit refund, bond exit; missing inputs give computable=false); statute context from a local read-only SQLite index (curated topic_map.yaml; 409 STATUTE_INDEX_UNAVAILABLE without it); pre-lawyer brief in JSON and Markdown. Written, not run: tests/test_phase3_*.py, tests/redteam/questions.yaml, smoke_api.py --phase 3. Not built: tool-calling agent mode (cut list; agent.mode is now 'pipeline'); the real statute index (scripts/build_statute_index.py needs Open India Law access and has not been run; its column names are unverified). Contract examples for ask/scenarios/statutes/brief are still hand-written. | `backend/src/lexishield/agents/{router,ask,scenarios,relevance}.py`, `triage/`, `scenarios/`, `statutes/` |
| P4–P6 | Not started | |

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
