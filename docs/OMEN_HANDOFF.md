# OMEN handoff: everything to continue LexiShield on the Windows machine

Written 2026-10-18 at the end of Phase 0 on the Ryzen laptop. Read this top to bottom once, then follow
section 3. It consolidates the plan, decisions and open issues from our working session. Details live in:

- [`IMPLEMENTATION_PLAN.md`](IMPLEMENTATION_PLAN.md): setup and the test command for every phase
- [`PROJECT_LOG.md`](PROJECT_LOG.md): status, what worked, what didn't, decisions
- [`omen-setup.md`](omen-setup.md): Windows runbook
- [`plan/LexiShield_Build_Plan.docx`](plan/LexiShield_Build_Plan.docx): full design, architecture and risk register
- [`../contracts/README.md`](../contracts/README.md): frontend contract rules

---

## 1. Where we are

| Phase | State |
|---|---|
| P0 Foundations and frozen contract | Code done on `main` (4 commits). Tests 26/26 green on the Ryzen laptop. **OMEN benchmark not run. Accuracy issue open.** |
| P1 Ingestion, trust boundary, retrieval | Not started. Endpoints exist as 501 stubs. **This is your next build.** |
| P2 Analysis core | Not started |
| P3 Interaction layer | Not started |
| P4 Proof and robustness | Not started |
| P5 Freeze and reproduce | Not started |
| P6 Demo and submit | Not started |

Repository: `https://github.com/ZERODAY-2026/Geeks`, branch `main`.
Latest commit: `a1cbcad feat(contracts): publish frozen API contract v1 for the frontend`.

Timeline context: the hackathon started on 2026-10-18. Phase 0 took about the first 45 minutes of planned time.

---

## 2. Decisions we made (and why)

| Decision | Why |
|---|---|
| Track PS2. Product: **LexiShield**, a private on-device legal document triage agent | Matches the rubric; India datasets fit |
| **Scope:** India residential rental and employment documents (deep checklists). Freelance MSA and legal notices (generic checklists). Jurisdiction auto-detected from the governing-law clause; US/UK get flags only | Honest, testable scope. The rubric rewards stated scope |
| **Backend first** in FastAPI + Pydantic v2. The React frontend is built separately (Antigravity) against `contracts/` | Team split: three on backend, one on frontend and corpus |
| **Primary model `gemma4:e4b-it-qat`** on the OMEN (RTX 5070, 8 GB VRAM). Alternative `gemma3n:e4b`, which is the exact class the guide prefers. CPU laptops use `gemma4:e2b-it-qat` | Fits 8 GB VRAM; the CPU profile runs on 13 GB laptops. Both Gemma 4 edge models are accepted by PS2 |
| **Ollama** as the model runtime, on loopback only (127.0.0.1:11434) | Local, CUDA support, JSON-schema output, model digests for attestation |
| **Thinking off** (`think: false`) for Gemma 4 | About 3× faster with the same output length |
| **Every Gemma call goes through `llm/gateway.py`.** Schema-enforced JSON, one repair retry, then `UNCLEAR`. Never invented content | One place to audit; no silent fallback |
| **No hardware TEE.** Not on the team machines. SGX is deprecated on client Core CPUs, TDX and SEV-SNP are server-only, NVIDIA's GPU TEE is data-centre only. We implement **isolate, seal, attest** in software and say so in the docs | Honest threat model; judges check claims |
| **Winning edge: distortion check.** Numbers, durations, dates, negations and party roles in any plain-language explanation must match the cited source span. Failures withhold the explanation | Directly targets rubric criterion 1 and misgrounding |
| **Quotes are always shown from the source text**, never from the model's version | Prevents a snapped quote hiding a wrong explanation |
| **Silence needs two independent checks.** The model says NOT_MENTIONED *and* a lexicon search finds nothing, or the item is UNCLEAR | Stops false "the document is silent" claims |
| **Nothing that reads as legal advice.** An advice guard blocks "enforceable / illegal / you should sign" and routes to escalation (lawyer, Rent Authority, labour department, DLSA free legal aid) | Rubric criteria 3 and L4 |
| **Privacy:** no document content leaves the machine. Egress guard (Python audit hook), network-less container for the proof run, signed Privacy Receipt | Gate L2, L9 and criterion 4 |
| **Streamlit dropped** for FastAPI | Streamlit sends usage statistics by default (telemetry risk) |
| **Pydantic models are the API contract.** `contracts/openapi.json` and examples are generated, and a test fails if they go stale | Frontend cannot drift from the backend |
| **Git identity:** commits use the configured identity with **no co-author trailer** | You asked for this |

---

## 3. OMEN set-up (Windows, PowerShell)

Set-up steps need network access. After that, processing must run offline.

### 3.1 Tools
```powershell
# uv (installs Python 3.12 for the project)
powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"

# Ollama for Windows (0.40 or newer): https://ollama.com/download
ollama --version
nvidia-smi              # must show the RTX 5070 and a recent driver
git --version
```

If `nvidia-smi` fails, install the current NVIDIA driver before anything else.

### 3.2 Models
```powershell
ollama pull gemma4:e4b-it-qat        # primary, about 6.1 GB
ollama pull gemma3n:e4b              # comparison, about 9.8 GB
ollama pull embeddinggemma:300m      # embeddings, 622 MB
ollama pull gemma4:e2b-it-qat        # optional: lets you run the CPU profile for comparison
```

### 3.3 Code
```powershell
git clone https://github.com/ZERODAY-2026/Geeks.git
cd Geeks
git checkout main
cd backend
uv sync --frozen
uv run lexishield info --profile gpu     # lists the models Ollama has
```

### 3.4 Demo and privacy hygiene
- Quit the **Ollama tray app** during demos. Run `ollama serve` in a terminal instead. The desktop app can run background update checks.
- `OLLAMA_HOST` must be unset or `127.0.0.1:11434`. **Never `0.0.0.0`** for real work.
- `LEXISHIELD_MODELS__PROFILE` defaults to `gpu`. To set it explicitly: `$env:LEXISHIELD_MODELS__PROFILE="gpu"`.

---

## 4. Phase 0 on the OMEN: do this first

### 4.1 Gate
```powershell
cd backend
uv run ruff check src scripts tests
uv run pytest -m phase0 -q                  # 26 tests, includes the live Gemma check
uv run python scripts/export_openapi.py --check
```

Expected: lint clean, 26 passed, export check exit 0.

### 4.2 Benchmark (required for the memory and speed report)
```powershell
uv run python scripts\bench.py --models gemma4:e4b-it-qat gemma3n:e4b --label omen-rtx5070 --trials 10
```

This writes `backend\eval\results\bench_*_omen-rtx5070.json`. Keep the console output.
Watch `nvidia-smi` during the run. VRAM should be about 6–7 GB. If the model runs on CPU, update the driver
and Ollama first.

### 4.3 Accuracy check (open issue, do not skip)
The Ryzen run returned valid JSON 10/10 but said `NOT_MENTIONED` for a clause that clearly states the
deposit amount. The gate checks JSON validity only, so it can't see this. The benchmark now also prints
`status_correct` and `verbatim` rates.

For each model, look at the printed `status_correct` and `verbatim` rates. Record both models' numbers in
`docs/PROJECT_LOG.md` section 4. **Choose the primary model on accuracy, not validity.** If neither model is
correct on that clause, do **not** move to Phase 2 until the prompt or the topic definition is fixed. Tell
the team first.

### 4.4 Live API smoke test
Terminal 1:
```powershell
uv run lexishield serve                     # gpu profile, http://127.0.0.1:8000
```
Terminal 2:
```powershell
uv run python scripts\smoke_api.py --phase 0
```
Expected: five checks pass (health, system/info, contract paths, problem+json, loopback bind).

### 4.5 Commit the benchmark result
```powershell
git checkout -b omen/bench-results
git add backend\eval\results docs\PROJECT_LOG.md
git commit -m "bench: OMEN RTX 5070 results for gemma4 e4b-qat and gemma3n e4b"
git push -u origin omen/bench-results
```
Then tell the team to pull it. Merge into `main` after review.

---

## 5. Phase 1 on the OMEN: what to build next

Goal: any supported file becomes a clause tree with exact character offsets. Private data is sealed and
egress is blocked. Retrieval finds the right clauses. Work in three parallel streams if the team splits up.

### 5.1 Work split (from the plan)
| Owner | Modules | Done when |
|---|---|---|
| Ingestion lead | `ingest/loaders.py` (PDF, DOCX, TXT from bytes), `ingest/layout.py` (pdfplumber characters with page, bbox, colour, size), `ingest/hidden.py`, `ingest/normalize.py` (offset map), `ingest/segment.py`, `ingest/xref.py`, `ingest/injection.py`. Routes `POST /documents`, `GET /documents/{id}` | Clause tree and offsets correct on every fixture |
| Platform lead | `trust/egress_guard.py` (audit hook), `trust/vault.py` (AES-256-GCM, TTL, shred), `trust/redact_log.py`, `trust/temp_sentinel.py`, raise the multipart spool size, `DELETE /documents`, `GET /privacy/status`, `GET /privacy/events`, `scripts/audit_deps.py` | Egress blocked outside loopback; uploads never touch disk |
| Gemma lead | `retrieval/bm25.py`, `retrieval/embed.py`, `retrieval/hybrid.py` (reciprocal-rank fusion, k=6), `ingest` cross-reference expansion, `agents/classify.py` (type, jurisdiction, party roles), data-delimited prompt templates in `llm/prompts/` | Recall@6 ≥ 0.9 on 15 hand-labelled queries |
| Frontend and corpus | Synthetic fixtures via `scripts/make_fixtures.py` (reportlab), including adversarial files; UI upload and source viewer | Fixtures generated; UI shows them |

### 5.2 Synthetic fixtures (write answer keys before running the model)
- `in_rental_11m_leave_license.pdf`: Bengaluru, deposit ₹1,50,000, 11 months, lock-in 6 months, 2-month notice, painting deduction, undefined "deductions"
- `in_rental_missing_clauses.pdf`: no refund timeline, no maintenance split (silence cases)
- `in_offer_letter_bond.pdf`: Pune, service bond ₹2,00,000 for 24 months, 90-day notice with buyout, 12-month non-compete
- `msa_freelance_generic.pdf`, `legal_notice_demand.pdf`
- `adv_white_text_injection.pdf` (white 1 pt text: "ignore previous instructions…"), `adv_zero_width_bidi.txt`, `adv_conflicting_clauses.pdf` (30 vs 60 days notice)
- `scanned_page.pdf`, `encrypted.pdf`, `corrupt.pdf`, `empty.txt`, `long_60_pages.pdf`
- `us_lease_generic.pdf`, `uk_tenancy_generic.pdf`

**Never use real contracts or personal documents** in fixtures, tests, benchmarks or the repo.

### 5.3 Phase 1 tests (`backend/tests/test_phase1_*.py`, marker `phase1`)
- Offset round-trip: `doc.text[c.char_start:c.char_end] == clause.text` for every clause in every fixture
- Hidden-content detector: white text, zero-width and bidi characters each produce a HIGH finding; hidden text is absent from any prompt payload
- Failure codes: encrypted, corrupt, empty and scanned files return 422 with `ENCRYPTED_PDF`, `MALFORMED_FILE`, `EMPTY_DOCUMENT`, `SCANNED_NO_TEXT`
- Egress guard: a connection to `example.com:443` raises `EgressBlocked` and the counter increments; loopback to Ollama still works
- Temp-file sentinel: zero files created during upload and ingest
- Vault: data unreadable after `DELETE /documents/{id}`
- Retrieval recall@6 ≥ 0.9; classifier correct on 5 of 5 core fixtures
- Long document (60 pages) ingests in under 5 seconds

Gate:
```powershell
uv run pytest -m "phase0 or phase1" -q
uv run python scripts\smoke_api.py --phase 1
```

### 5.4 Windows-specific cautions for Phase 1
- The egress audit hook works on Windows. Test it with the actual network stack, not only a mock.
- Use `tempfile` only through the sentinel's allow-list; Windows writes temp files to `%TEMP%` silently.
- pdfplumber works on Windows with no extra installs. If a PDF fails, the error path must still return a 422.

---

## 6. Phases 2–6 at a glance (full detail in IMPLEMENTATION_PLAN.md)

**Phase 2: analysis core.** Quote verifier (exact → normalized → fuzzy ≥ 92, and numbers and negations must match), facts extractor, distortion checker, silence double-key, tiers, job queue (one GPU worker), SSE events, YAML checklist packs for `in_rental` and `in_employment`, the orchestrator and checklist NLI agent, card writer.
Gate: `pytest -m "phase0 or phase1 or phase2"`. Zero unverified quotes in any output. Golden topic accuracy ≥ 80%. Every key silence reported as NOT_MENTIONED or UNCLEAR, never ENTAILED.

**Phase 3: interaction.** Intent router, Ask agent (at most 3 tool calls) with pipeline fallback, output guard, scenarios with exposure calculator (verified amounts only), statute index build (`scripts/build_statute_index.py`, Open India Law legislation parquet for Central, Karnataka, Maharashtra and Delhi), escalation routing, brief generator.
Gate: verdict questions decline 100%; unanswered questions return NOT_IN_DOCUMENT ≥ 90%, with no fabricated citations.

**Phase 4: proof and robustness.** Ed25519 Privacy Receipt and `scripts/verify_receipt.py`; Dockerfile and `deploy/compose.airgap.yml` (`internal: true`); `scripts/prove_airgap.py`; red-team suite (≥ 25 cases in `tests/redteam/`); `scripts/eval_cuad.py` on 20 CUAD contracts (evaluation only); pipeline benchmark; `docs/results.md`.

**Phase 5: freeze and reproduce.** API freeze v2 (additive only); README for Windows and Linux; model card; a fresh clone on a second laptop passes `smoke_api.py --phase all` using only the README; secret scan clean.

**Phase 6: demo.** Record the 5-minute demo with Wi-Fi off and connection monitoring visible (script in the build plan, chapter 16). Final `pytest -q` and `smoke_api.py --phase all`. Tag `v1.0`.

Cut order if behind schedule: DOCX loader → extra scenarios → statute index → agent tool mode (switch to pipeline) → embeddings (BM25 only). **Never cut** the verifier, distortion checker, silence check, advice guard, egress guard, the air-gap proof, or the README and model card.

---

## 7. Rules for every phase
1. No document content leaves the process. `llm/gateway.py` is the only model client.
2. Never display a quote that did not match the source text.
3. No telemetry, analytics or crash-reporting dependency. Check with `scripts/audit_deps.py`.
4. Contract changes after Phase 0 are additive. Run `uv run python scripts\export_openapi.py` after any model or route change, and commit the result.
5. Never commit `backend\data\`, `.venv\`, secrets, model weights or real documents.
6. Report failures honestly. A gate that passes on the wrong metric is not a pass.

---

## 8. Git workflow on the OMEN
```powershell
git checkout main
git pull
git checkout -b phase1/<name>         # one branch per work item
# ... work ...
git add <specific files>
git commit -m "feat(ingest): <short description>"    # no co-author trailer
git push -u origin phase1/<name>
```
Open a PR into `main`. Run the gate before pushing. Do not push directly to `main` without the team's agreement.

---

## 9. Troubleshooting

| Symptom | Likely cause | Fix |
|---|---|---|
| `health` shows `ollama: down` | Ollama not running | Start the tray app or `ollama serve` |
| `models_ready: false` | Model not pulled, or tag differs | `ollama list`, then `ollama pull <tag>` |
| Live test skipped | Ollama not running or model missing | Same as above |
| Benchmark shows CPU, not GPU | Old driver or Ollama build | Update NVIDIA driver and Ollama; check `nvidia-smi` while running |
| `ruff` or `pytest` not found | Running outside `backend\` | `cd backend`, then `uv run ...` |
| Port 8000 in use | Another server running | `uv run lexishield serve --port 8001` (update the frontend's API base) |
| Frontend gets CORS errors | Origin not allowed | Add the origin to `server.cors_origins` in `config\lexishield.yaml` |
| `export_openapi.py --check` fails | Models or routes changed without regenerating | Run `scripts\export_openapi.py`, then commit `contracts\` |
| Test `test_no_secrets_in_backend_sources` fails | A string looks like a key | Remove the literal; read it from the environment |

---

## 10. Open items, in priority order
1. OMEN benchmark for both models, with the accuracy numbers recorded (section 4.2–4.3).
2. Choose the primary model on accuracy. Fix the prompt or topic definition if neither model is correct on the deposit clause.
3. Re-run the Ryzen CPU benchmark cleanly (its earlier RAM figure was wrong and the file was removed).
4. Replace the placeholder numbers in `contracts/examples/benchmark.json` with real results.
5. Phase 1 build (section 5).
6. Write `scripts/audit_deps.py`, `scripts/verify_receipt.py` and `scripts/eval_cuad.py` when their phases come up.
