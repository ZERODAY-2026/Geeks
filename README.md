# LexiShield

**Private, on-device legal document triage, powered by Google Gemma.**
ZeroDay OSS Hacktoberfest 2026 · IIIT Dharwad · Track PS2 (Private Legal Document Triage Agent)

Upload a rental agreement, an employment contract or offer letter, a freelance agreement or a legal notice, and ask
questions about it in plain language. LexiShield answers **only from the document**: every statement cites the exact
passage, page and lines it comes from, and clicking a citation opens the document at that spot. When the document
does not answer a question, it says so. It refuses to give legal verdicts ("is this enforceable?", "should I sign?")
and points you to who can help instead.

Everything runs **on your machine**: Gemma runs locally in Ollama, the server listens only on 127.0.0.1, and once
installed it needs **no internet connection**. No document content leaves the device.

> LexiShield gives preliminary information to help you understand a document. It is **not legal advice** and
> cannot decide whether anything is legal or enforceable.

---

## Contents
1. [What it does](#1-what-it-does)
2. [How the answers stay grounded](#2-how-the-answers-stay-grounded)
3. [Requirements](#3-requirements)
4. [Install (once, online)](#4-install-once-online)
5. [Run (offline)](#5-run-offline)
6. [Using the app](#6-using-the-app)
7. [Measured results](#7-measured-results)
8. [Known limitations](#8-known-limitations)
9. [Development and tests](#9-development-and-tests)
10. [Repository layout](#10-repository-layout)

---

## 1. What it does

| Feature | What you get |
|---|---|
| **Upload** | PDF (with a text layer), DOCX or TXT, or pasted text. Kept in memory only, encrypted, never written to disk. |
| **Ask (chat)** | Plain-language answers grounded in the document. Each claim shows the exact quote with its page and lines. |
| **Open at the citation** | Clicking a citation shows that page with the cited words highlighted; "Open original" opens the uploaded PDF at that page. |
| **"Not in this document"** | If no clause answers a question, it says so and shows the closest clauses, instead of guessing. |
| **No legal verdicts** | Questions about legality, enforceability or whether to sign are declined, with the relevant clauses and who can help (lawyer, rent authority, labour department, free legal aid via DLSA). |
| **Full analysis** (optional) | A checklist of 10–18 topics per document type (deposit, notice, lock-in, bond, non-compete, ...), each marked stated, contradicted, unclear or **silent**, with plain-language cards. |
| **What-if scenarios** | Leaving a rental early, getting the deposit back, resigning during a bond. Totals use only amounts the document states; a missing amount is reported, never guessed. |
| **Lawyer brief** | A one-page summary (JSON or Markdown) of the issues, deadlines, silences and questions to ask. |
| **Privacy controls** | Hidden-text and prompt-injection detection, an egress guard that blocks any non-loopback connection, crypto-shredding on delete. |

Document types: India residential rental and employment (deep checklists), freelance agreements and legal notices
(general checklists). Documents from other countries are flagged as such.

## 2. How the answers stay grounded

```
upload ─► ingest (text, pages, clauses, exact offsets, hidden-text scan)
question ─► retrieve the relevant clauses (BM25 + EmbeddingGemma)
         ─► Gemma 4 (local, via Ollama) proposes claims with quotes
         ─► verification gate:
              1. every quote must match the cited clause (exact, normalized, or fuzzy with equal numbers and negations)
              2. every quote must address the question (a separate, narrow Gemma check per quote)
              3. every number, duration and date in a claim must appear in its quote (distortion check)
              4. no verdict language (advice guard)
         ─► only claims that pass all four are shown, quoted from the document itself, never from the model
```

If no claim survives, the answer is "not in this document". Verdict questions are declined by fixed rules before
the model is asked.

## 3. Requirements

| | |
|---|---|
| Operating system | Windows 10/11, or Linux |
| GPU | **NVIDIA with at least 8 GB of memory** (developed on an RTX 5070 Laptop GPU, 8 GB). CPU-only is not supported. |
| Disk | About 10 GB free (models 6.7 GB, plus Python and Node packages) |
| Software | [Ollama](https://ollama.com/download) 0.40 or newer, [Node.js](https://nodejs.org) 18 or newer, Git. The installer adds [uv](https://docs.astral.sh/uv/) (Python 3.12 and packages) if it is missing. |
| Internet | Only during installation. |

## 4. Install (once, online)

```bash
git clone https://github.com/ZERODAY-2026/Geeks.git
cd Geeks
```

**Windows (PowerShell)**
```powershell
powershell -ExecutionPolicy Bypass -File .\install.ps1
```

**Linux**
```bash
bash install.sh
```

The installer:
1. checks the NVIDIA GPU (8 GB or more), Ollama and Node.js, and installs uv if needed;
2. installs the backend with the exact package versions from `backend/uv.lock`;
3. downloads the models: `gemma4:e4b-it-qat` (chat) and `embeddinggemma:300m` (retrieval);
4. installs the small offline data the app needs (NLTK `cmudict`, for reading-level scores);
5. builds the web app (`frontend/dist`).

It ends with `LexiShield is installed. You can now disconnect from the internet.`

## 5. Run (offline)

**Windows**
```powershell
powershell -ExecutionPolicy Bypass -File .\run.ps1
```

**Linux**
```bash
bash run.sh
```

The run script starts Ollama if needed, loads Gemma into GPU memory, starts LexiShield on
**http://127.0.0.1:8000** and opens it in your browser. Stop it with Ctrl+C.

On Windows, quit the Ollama tray app before a demo; the run script starts `ollama serve` itself. The app shows a red
banner if Gemma is not running or a model is missing.

Details of what keeps it offline: [`docs/OFFLINE.md`](docs/OFFLINE.md).

## 6. Using the app

1. **Upload** a PDF, DOCX or TXT (or paste text).
2. **Ask** a question in the chat, e.g. "How much is the security deposit?" or "What is the notice period?".
   - Each answer lists its claims with citation chips such as `p. 1, lines 7-8 · C4`.
   - **Click a citation** to open the source viewer at that page with the quoted words highlighted.
   - **Open original** opens the uploaded file; a PDF opens at the cited page in your browser's built-in viewer.
3. Optional: **Run Full Pipeline** (document menu) for the checklist, cards and silences. Then try **Life Scenarios**
   and **Export Brief**.
4. **Close & Shred** removes the document and everything derived from it from memory.

Starter questions appear for the detected document type; any question can be asked.

## 7. Measured results

All on synthetic test documents written for this project (no real contracts), on the RTX 5070 with
`gemma4:e4b-it-qat`. Answer keys were written before each run. Small samples: treat these as evidence, not proof.

| Check | Result |
|---|---|
| Checklist, held-out documents never used for tuning (3 runs each) | rental 100%, employment 94%, legal notice 90% of topics correct |
| Silence: a topic the document does not cover is never reported as stated | held on every held-out run |
| Ask, held-out questions (written before the run) | 10/10 answered with the right fact cited; 10/10 out-of-document questions answered "not in this document" |
| Verdict questions declined | 25/25 phrasings (rules), 4/4 end to end |
| Every displayed quote is the document's own text | enforced by the gate and checked in every test |
| Live end-to-end smoke test (upload, ask, analyse, scenarios, brief) | 18/18 checks |

The decision log, including what failed and how it was fixed, is in [`docs/PROJECT_LOG.md`](docs/PROJECT_LOG.md).

## 8. Known limitations

- **NVIDIA GPU only.** The CPU model profile exists in the configuration but has not been tested.
- **Scanned PDFs** without a text layer are rejected with a clear message; there is no OCR.
- **DOCX and TXT** are shown as their extracted text with the citation highlighted (browsers cannot display DOCX).
  For PDFs, the highlight is shown on the extracted text; the original PDF opens at the right page without a highlight.
- **Each chat message is answered on its own.** Follow-ups such as "and the refund?" should be asked as full questions.
- **Statute context** (Open India Law sections next to topics) needs a local index built with
  `backend/scripts/build_statute_index.py`, which needs access to the gated dataset; without it the app says the index
  is not installed.
- Legal notices: deadlines phrased as "pay within N days" are sometimes marked unclear rather than stated.
- English documents; checklists are written for India.

## 9. Development and tests

```bash
# Backend API with auto-reload off, loopback only
cd backend
uv run lexishield serve                     # http://127.0.0.1:8000 (also serves frontend/dist if built)

# Frontend dev server with hot reload; /api is proxied to the backend
cd frontend
npm run dev                                  # http://localhost:5173

# Tests (fast, no model needed)
cd backend
uv run pytest -m "phase0 or phase1 or phase2 or phase3" -q --ignore=tests/test_phase2_golden.py \
  --ignore=tests/test_phase2_holdout.py --ignore=tests/test_phase2_fresh3.py \
  --ignore=tests/test_phase3_redteam.py --ignore=tests/test_phase3_heldout.py

# Live model checks (Ollama running, models pulled)
uv run pytest tests/test_phase3_redteam.py tests/test_phase3_heldout.py -q
uv run python scripts/smoke_api.py --phase 3            # against a running server
uv run python scripts/export_openapi.py --check         # API contract is up to date
```

Configuration lives in `backend/config/lexishield.yaml`; any value can be overridden with
`LEXISHIELD_<SECTION>__<KEY>` (for example `LEXISHIELD_SERVER__PORT=8001`). The server refuses non-loopback addresses.
The API contract for the frontend is [`contracts/`](contracts/README.md): `openapi.json`, real example responses, and
how to render answers and open citations.

| Phase | Scope | Status |
|---|---|---|
| P0 | Foundations, model gateway, benchmarks, API contract | done |
| P1 | Ingestion, trust boundary, retrieval | done |
| P2 | Checklist, cards, verification gate, jobs and live progress | done |
| P3 | Ask, scenarios, statute lookup, lawyer brief, frontend integration | done (statute index not built) |
| P4–P6 | Air-gap proof, signed receipts, red-team suite, CUAD evaluation, freeze | not started |

## 10. Repository layout

```
install.ps1 / install.sh   one-time installer (online)
run.ps1 / run.sh           start the app (offline)
backend/                   Python 3.12 FastAPI service (uv project)
  src/lexishield/            ingest/, retrieval/, agents/, verify/, triage/, trust/, api/, llm/
  packs/                     checklists per document type (YAML)
  scenarios/ escalation/     what-if scenarios and escalation routes (YAML)
  config/lexishield.yaml     all settings
  tests/                     phase tests, fixtures (synthetic), red-team questions
  scripts/                   offline prep, benchmarks, evaluation, contract export
frontend/                  React + Vite + Tailwind app (built into frontend/dist)
contracts/                 API contract for the frontend
docs/                      plan, project log, offline guide
```

## Licence and attributions

Code: Apache-2.0 (see [LICENSE](LICENSE)). Model and dataset terms: see [NOTICE](NOTICE).
