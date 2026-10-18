# LexiShield

**Private, on-device legal document triage, powered by Google Gemma.**  
*ZeroDay OSS Hacktoberfest 2026 · IIIT Dharwad · Track PS2 (Private Legal Document Triage Agent)*

---

LexiShield analyzes residential rental agreements, employment contracts, freelance service agreements (MSA/SOW), and legal demand notices **entirely on your local machine**. It translates dense legal clauses into plain language, explicitly highlights when a document is **silent** on critical statutory protections, verifies every claim against exact source text offsets, refuses to provide legal verdicts, and routes users to appropriate legal authorities (e.g., District Legal Services Authorities, Rent Controllers, Labour Departments, or specialized advocates). 

**Zero document bytes, derived text, or embeddings ever leave the local device.**

> **Legal Disclaimer:** LexiShield provides preliminary triage, clause extraction, and structured information to assist in document comprehension. It does **not** provide legal advice, does not establish an attorney-client relationship, and cannot assess the formal legality, validity, or enforceability of any agreement. Users should consult a qualified legal professional or authorized legal aid organization before taking action.

---

## Table of Contents

1. [Implementation Status](#implementation-status)
2. [Architecture & Workflow](#architecture--workflow)
   - [System Architecture (Mermaid)](#1-system-architecture)
   - [End-to-End Workflow & Verification Pipeline (Mermaid)](#2-end-to-end-workflow--verification-pipeline)
3. [System Requirements & Dependencies](#system-requirements--dependencies)
4. [Installation & Setup](#installation--setup)
5. [Configuration & Model Profiles](#configuration--model-profiles)
6. [Run Commands](#run-commands)
7. [API Verification & Usage Examples](#api-verification--usage-examples)
8. [Testing & Benchmark Gates](#testing--benchmark-gates)
9. [Privacy Architecture & Local Trust Boundary](#privacy-architecture--local-trust-boundary)
10. [Datasets, Models & Licences](#datasets-models--licences)
11. [Repository Structure](#repository-structure)
12. [Troubleshooting & Known Limitations](#troubleshooting--known-limitations)

---

## Implementation Status

LexiShield follows a strict phase-gate build plan defined in [`docs/plan/LexiShield_Build_Plan.docx`](docs/plan/LexiShield_Build_Plan.docx). Every phase enforces cumulative automated test gates and strict contract freezes.

| Phase | Subsystem Scope | Status | Verification Evidence |
|---|---|---|---|
| **Phase 0** | **Foundations, LLM Gateway & Frozen API Contract** | **COMPLETED & VERIFIED** | 26/26 unit tests passing (`pytest -m phase0`); frozen OpenAPI 3.1 specification & examples in `contracts/`; RFC 9457 `problem+json` error envelope; loopback bind enforcement; live Gemma structured output validation; OMEN RTX 5070 benchmark recorded (`eval/results/bench_gemma4-e4b-it-qat_omen-rtx5070.json`). |
| **Phase 1** | **Ingestion, Trust Boundary & Hybrid Retrieval** | **COMPLETED & VERIFIED** | 71/71 tests passing (`pytest -m "phase0 or phase1"`); smoke test 11/11 passing (`scripts/smoke_api.py --phase 1`); in-memory PDF/DOCX/TXT parsers with character offset maps; hidden-text & injection quarantine; AES-256-GCM sealed vault with crypto-shredding; temp-file sentinel (0 disk writes); socket egress guard; BM25 + EmbeddingGemma hybrid retrieval with RRF. |
| **Phase 2** | **Analysis Core, Checklist Packs & Verification Gate** | ⏳ **Planned** *(Contract Frozen)* | Endpoints return `501 NOT_IMPLEMENTED`. Contract includes: YAML topic packs (`in_rental.yaml`, `in_employment.yaml`), tri-state NLI (ENTAILED, CONTRADICTED, NOT_MENTIONED, UNCLEAR), fact distortion checker, silence double-key, asyncio job queue, and SSE progress stream (`/jobs/{id}/events`). |
| **Phase 3** | **Interactive Layer: Grounded Q&A, Scenarios & Statutes** | ⏳ **Planned** *(Contract Frozen)* | Endpoints return `501 NOT_IMPLEMENTED`. Contract includes: Bounded tool-calling Ask agent (max 3 calls), Legal Advice Guard (`LEGAL_VERDICT_DECLINED`), what-if financial scenario engine, SQLite FTS5 statute context index (Open India Law), and pre-lawyer markdown brief. |
| **Phase 4** | **Air-gap Proof, Signed Receipts, Red Team & CUAD Eval** | ⏳ **Planned** *(Contract Frozen)* | Contract includes: Docker network-isolated prover run, Ed25519-signed Privacy Receipts (`/privacy/receipts`), 25+ adversarial injection red-team test suite, and 20-contract CUAD v1 benchmark evaluation. |
| **Phase 5** | **Freeze, Clean-Clone Reproduction & Demo Submission** | ⏳ **Planned** | Clean clone reproduction script, dependency telemetry scan, zero-secret verification, and offline demo recording. |

---

## Architecture & Workflow

The architecture is derived directly from Sections 6–9 of [`docs/plan/LexiShield_Build_Plan.docx`](docs/plan/LexiShield_Build_Plan.docx). It divides processing into ten modular subsystems across five sequential pipeline stages, enclosed within a Local Trust Boundary.

### 1. System Architecture

```mermaid
flowchart TD
    UI["Web UI / CLI Client<br/>(Local React bundle • No external CDNs/telemetry)"]

    subgraph Gateway["API Gateway & Local Trust Boundary (FastAPI · Loopback 127.0.0.1)"]
        API["REST & SSE Endpoints<br/>/documents • /analyze • /ask • /report"]
        VAULT["Sealed In-Memory Vault<br/>(AES-256-GCM Session Key • 0 Disk Writes)"]
        EG["In-Process Egress Guard<br/>(Blocks Non-Loopback Sockets)"]
        API --- VAULT
        EG -.->|Enforces Loopback| API
    end

    subgraph Pipeline["Five-Stage Processing Pipeline"]
        direction LR
        STAGE1["1. Ingestion & Sanitization<br/>PDF/DOCX/TXT Parser • Offset Map"] --> STAGE2["2. Hybrid Retrieval<br/>BM25 + EmbeddingGemma (RRF)"] --> STAGE3["3. Gemma Orchestration<br/>Checklist DAG • Structured NLI"] --> STAGE4["4. Verification Gate<br/>Quote Match • Distortion & Advice Guards"] --> STAGE5["5. Triage & Escalation<br/>Severity • India Escalation Routes"]
    end

    subgraph Runtime["Local Inference Runtime"]
        OLLAMA["Ollama Runtime (127.0.0.1:11434)<br/>• Gemma 4 Chat: gemma4:e4b-it-qat (GPU) / e2b (CPU)<br/>• Embeddings: embeddinggemma:300m"]
    end

    UI -->|HTTP / SSE| API
    API --> STAGE1
    STAGE3 <-->|Strict Structured JSON| OLLAMA
    STAGE5 -->|Cache Report| VAULT
```

---

### 2. End-to-End Workflow & Verification Pipeline

```mermaid
flowchart TD
    subgraph Step1["1. Ingestion & Sanitization (Phase 1: Verified)"]
        UPLOAD["User Upload: PDF / DOCX / TXT<br/>POST /api/v1/documents"]
        SPOOL["In-Memory Buffer<br/>Cap: 20 MB (0 disk writes verified by Sentinel)"]
        PARSE["File Parsers & Layout Extraction<br/>pdfplumber / python-docx / UTF-8 text"]
        SCAN["Sanitization & Security Scans<br/>Hidden Text Scan + Prompt Injection Quarantine"]
        OFFSET["Normalizer & Global Offset Map<br/>Exact round-trip: doc.text[start:end] == clause.text"]
        SEGMENT["Clause Segmentation & Linking<br/>Hierarchical C1..Cn + Definitions + X-Refs"]
        VAULT_IN["Sealed In-Memory Vault<br/>AES-256-GCM session key (in RAM only)"]
        SUMMARY["201 Created: DocumentSummary<br/>id, pages, clause count, warnings, quick detect"]

        UPLOAD --> SPOOL --> PARSE --> SCAN --> OFFSET --> SEGMENT --> VAULT_IN --> SUMMARY
    end

    subgraph Step2["2. Job Trigger & Progressive SSE Streaming (Phase 2: Planned)"]
        START["Trigger Analysis<br/>POST /api/v1/documents/{id}/analyze"]
        QUEUE["Asyncio Job Queue<br/>Returns 202 Accepted (job_id)"]
        SSE_OPEN["Client Opens SSE Event Stream<br/>GET /api/v1/jobs/{job_id}/events"]
        CLASSIFY["Gemma Document Classification<br/>DocType + Jurisdiction + Party Roles"]
        PACK_SEL["Load Checklist Pack (YAML)<br/>e.g. in_rental.yaml, in_employment.yaml"]

        SUMMARY --> START --> QUEUE --> SSE_OPEN
        SSE_OPEN --> CLASSIFY --> PACK_SEL
    end

    subgraph Step3["3. Per-Topic NLI & Verification Pipeline (Phase 2: Planned)"]
        RETRIEVE["Hybrid Retrieval per Topic<br/>BM25 + EmbeddingGemma (RRF k=6) + X-Refs"]
        LLM_CALL["Gemma 4 Structured NLI Inference<br/>Schema: Status, Evidence Quotes, Plain Explanation"]
        GATE{"Verification Gate<br/>Automated Checks"}

        Q_CHECK["1. Quote Verifier<br/>Match quote to original document offset"]
        S_CHECK["2. Silence Double-Key<br/>If NOT_MENTIONED + Lexicon hit -> UNCLEAR"]
        D_CHECK["3. Distortion Checker<br/>Verify numbers, dates, durations, negation & roles"]
        A_CHECK["4. Legal Advice Guard<br/>Regex blocks verdicts (enforceable, illegal, etc.)"]

        VERIFIED["Output: Verified ClauseCard & ChecklistItem<br/>Confidence Tier + Reading Grade Calculation"]
        STREAM_CARD["Emit Progressive SSE Events<br/>event: checklist.item & event: card.ready"]

        PACK_SEL --> RETRIEVE --> LLM_CALL --> GATE
        GATE --> Q_CHECK --> S_CHECK --> D_CHECK --> A_CHECK --> VERIFIED --> STREAM_CARD
    end

    subgraph Step4["4. Triage Synthesis & Report (Phase 2: Planned)"]
        TRIAGE["Triage Aggregator<br/>Severity Rules + Exposure Arithmetic (Rent, Deposit)"]
        ESCALATION["India-First Escalation Router<br/>Lawyers, Rent Authority, Labour Dept, DLSA"]
        VAULT_SAVE["Store Final TriageReport<br/>Encrypted in In-Memory Vault"]
        REPORT_READY["Emit SSE: event: report.ready<br/>document_id, report_url"]
        REPORT_GET["Client Fetches Full Report<br/>GET /api/v1/documents/{id}/report"]

        STREAM_CARD --> TRIAGE --> ESCALATION --> VAULT_SAVE --> REPORT_READY --> REPORT_GET
    end

    subgraph Step5["5. Interactive Layer & Crypto-Shredding (Phase 3 & 4: Planned)"]
        ASK["User Grounded Q&A<br/>POST /api/v1/documents/{id}/ask"]
        ROUTER{"Ask Intent Router"}
        DECLINED["Legal Verdict Bait<br/>Refusal: LEGAL_VERDICT_DECLINED + Escalation"]
        ANSWERED["Factual / Plain Query<br/>ANSWERED with Verified Clause Citations"]
        NOT_FOUND["Uncovered Topic<br/>NOT_IN_DOCUMENT + Nearest Related Clauses"]

        BRIEF["Pre-Lawyer Escalation Brief<br/>GET /api/v1/documents/{id}/brief (JSON/Markdown)"]
        DELETE["Crypto-Shred Document<br/>DELETE /api/v1/documents/{id}"]
        SHRED_ACTION["Vault Discards AES-256-GCM Key<br/>Data becomes immediately unrecoverable (404)"]

        REPORT_GET --> ASK --> ROUTER
        ROUTER -->|Verdict Bait| DECLINED
        ROUTER -->|Document Fact| ANSWERED
        ROUTER -->|Absent Topic| NOT_FOUND
        REPORT_GET --> BRIEF
        REPORT_GET --> DELETE --> SHRED_ACTION
    end
```

---

## System Requirements & Dependencies

### Hardware Profiles

| Profile | Target Architecture | VRAM / RAM | Primary Chat Model | Embeddings Model | Measured Speed |
|---|---|---|---|---|---|
| `gpu` *(Default)* | NVIDIA GPU (tested on RTX 5070 Laptop GPU, 8 GB VRAM) | 8 GB+ VRAM, 16 GB+ System RAM | `gemma4:e4b-it-qat` (6.1 GB) | `embeddinggemma:300m` (622 MB) | ~61.7 tok/s gen |
| `cpu` | Standard x86_64 Laptop (tested on AMD Ryzen 7 7730U) | 12 GB+ System RAM | `gemma4:e2b-it-qat` (4.3 GB) | `embeddinggemma:300m` (622 MB) | ~16.0 tok/s gen |

### Software Prerequisites

- **Package Manager:** [`uv`](https://docs.astral.sh/uv/) (Astral's fast Python package runner; automatically manages and provisions Python 3.12).
- **Inference Server:** [Ollama](https://ollama.com) **0.40.0+**.
- **Version Control:** Git.
- **GPU Acceleration (GPU profile):** Current NVIDIA driver with `nvidia-smi` accessible on PATH.

### Real Dependency Management

There is **no `requirements.txt`**. Dependencies are declared in [`backend/pyproject.toml`](backend/pyproject.toml) and strictly pinned in [`backend/uv.lock`](backend/uv.lock):
- **Web & Streaming:** `fastapi>=0.143.3`, `uvicorn>=0.54.0`, `sse-starlette>=3.5.0`, `python-multipart>=0.0.32`
- **Typing & Validation:** `pydantic>=2.14.1`, `pydantic-settings>=2.16.0`, `pyyaml>=6.0.3`
- **Parsing & Offsets:** `pdfplumber>=0.11.10` (per-character bounding box and color extraction), `python-docx>=1.2.0`
- **Retrieval & Matching:** `rank-bm25>=0.2.2`, `numpy>=2.5.4`, `rapidfuzz>=3.14.6`
- **Model Client:** `ollama>=0.6.3`, `httpx>=0.28.1`
- **Security & Readability:** `cryptography>=50.0.2` (AES-256-GCM, Ed25519), `textstat>=0.7.13`, `psutil>=7.2.2`
- **Development & Test:** `pytest>=9.1.1`, `pytest-asyncio>=1.4.0`, `reportlab>=5.0.1`, `ruff>=0.17.1`

---

## Installation & Setup

Set-up time is the **only** time network access is required (to download dependencies and model weights). After setup, the application operates in an air-gapped environment.

### 1. Install `uv` and Ollama

**Linux / macOS:**
```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
# Install Ollama from https://ollama.com/download
```

**Windows (PowerShell):**
```powershell
powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
# Install Ollama from https://ollama.com/download
```

Verify installations:
```bash
uv --version
ollama --version
```

### 2. Download Model Weights via Ollama

Download the models for your hardware profile:

**GPU Profile (Default - NVIDIA 8 GB+ VRAM):**
```bash
ollama pull gemma4:e4b-it-qat
ollama pull embeddinggemma:300m
# Optional comparison baseline:
ollama pull gemma3n:e4b
```

**CPU Profile (Laptops without dedicated GPU):**
```bash
ollama pull gemma4:e2b-it-qat
ollama pull embeddinggemma:300m
```

### 3. Synchronize Dependencies

```bash
cd backend
uv sync --frozen
```

### 4. Verify Local Environment

Inspect the runtime models recognized by the gateway:
```bash
# GPU profile:
uv run lexishield info --profile gpu

# CPU profile:
uv run lexishield info --profile cpu
```

---

## Configuration & Model Profiles

Configuration is centralized in [`backend/config/lexishield.yaml`](backend/config/lexishield.yaml) and mapped to typed Pydantic models in [`backend/src/lexishield/settings.py`](backend/src/lexishield/settings.py). 

Every setting can be overridden via environment variables using the pattern `LEXISHIELD_<SECTION>__<KEY>`:

```yaml
server:
  host: 127.0.0.1            # Bound to loopback only; non-loopback is refused
  port: 8000
  cors_origins:
    - http://localhost:5173
    - http://127.0.0.1:5173
    - http://localhost:3000
  max_upload_mb: 20

ollama:
  host: http://127.0.0.1:11434
  keep_alive: 30m

models:
  profile: gpu               # gpu | cpu
  gpu:
    chat: gemma4:e4b-it-qat
    alt: gemma3n:e4b
    embed: embeddinggemma:300m
    num_ctx: 8192
  cpu:
    chat: gemma4:e2b-it-qat
    alt: gemma3n:e2b
    embed: embeddinggemma:300m
    num_ctx: 8192
  options:
    temperature: 0
    seed: 42
    timeout_s: 120
    max_parallel: 2
    think: false             # Thinking disabled: cuts latency ~3x with identical JSON output

verify:
  fuzzy_min: 92
  retrieval_k: 6

privacy:
  egress_allow: [127.0.0.1, "::1", localhost]
  session_ttl_s: 1800        # In-memory vault crypto-shreds inactive sessions after 30 mins
  receipts: true

features:
  statutes: true
  scenarios: true
  docx: true
  ocr: false                 # Scanned PDFs without text layer return 422 SCANNED_NO_TEXT
```

---

## Run Commands

### Start the Backend API

**Linux / macOS:**
```bash
cd backend
uv run lexishield serve --profile cpu
```

**Windows (PowerShell):**
```powershell
cd backend
# Runs on GPU profile by default
uv run lexishield serve

# Or explicitly select CPU profile:
$env:LEXISHIELD_MODELS__PROFILE="cpu"
uv run lexishield serve --profile cpu
```

- API Base URL: `http://127.0.0.1:8000/api/v1`
- Interactive OpenAPI Docs: `http://127.0.0.1:8000/docs`
- Raw OpenAPI Specification: `http://127.0.0.1:8000/api/v1/openapi.json`

> **Demo & Privacy Hygiene Tip:** On Windows, quit the Ollama system tray application before demos and start Ollama in a dedicated terminal (`ollama serve`) so the background desktop updater does not trigger outbound telemetry checks.

---

## API Verification & Usage Examples

All requests and responses use JSON (or multipart for uploads) and RFC 9457 `application/problem+json` for error reporting.

### 1. Health & Model Readiness (Implemented · P0)
```bash
curl -s http://127.0.0.1:8000/api/v1/health | jq .
```
```json
{
  "status": "ok",
  "ollama": "up",
  "models_ready": true,
  "missing_models": [],
  "version": "0.1.0"
}
```

### 2. Runtime & Hardware Inspection (Implemented · P0)
```bash
curl -s http://127.0.0.1:8000/api/v1/system/info | jq .
```
```json
{
  "app_version": "0.1.0",
  "profile": "gpu",
  "model": {
    "name": "gemma4:e4b-it-qat",
    "digest": "sha256:7b50849303d7...",
    "family": "gemma4",
    "parameter_size": "4.3B",
    "quantization": "Q4_K_M",
    "num_ctx": 8192
  },
  "ollama_version": "0.40.6",
  "gpu": "NVIDIA GeForce RTX 5070 Laptop GPU, 8151 MiB",
  "packs": ["in_employment", "in_rental", "msa_generic", "notice_generic"],
  "statute_index": { "available": false, "snapshot": null },
  "agent_mode": "tools"
}
```

### 3. Upload Document (Implemented · P1)
Upload a synthetic rental agreement (`PDF`, `DOCX`, or `TXT`):
```bash
curl -s -X POST http://127.0.0.1:8000/api/v1/documents \
  -F "file=@tests/fixtures/in_rental_11m_leave_license.pdf;type=application/pdf" | jq .
```
```json
{
  "document_id": "doc_e4c5b364817a",
  "filename": "in_rental_11m_leave_license.pdf",
  "mime": "application/pdf",
  "pages": 8,
  "char_count": 14280,
  "clause_count": 34,
  "scanned": false,
  "warnings": [],
  "hidden_findings": [],
  "quick_detect": {
    "doc_type": "rental",
    "country": "IN"
  },
  "created_at": "2026-10-18T08:12:00.000000Z"
}
```

### 4. Fetch Exact Clause with Offsets (Implemented · P1)
```bash
curl -s http://127.0.0.1:8000/api/v1/documents/doc_e4c5b364817a/clauses/C12 | jq .
```
```json
{
  "id": "C12",
  "number": "5",
  "heading": "SECURITY DEPOSIT",
  "page_start": 2,
  "page_end": 2,
  "char_start": 3810,
  "char_end": 4125,
  "text": "The Licensee shall pay an interest-free refundable security deposit of Rs. 1,50,000 (Rupees One Lakh Fifty Thousand only)...",
  "parent_id": null,
  "defined_terms": ["Security Deposit"],
  "xrefs": ["Clause 14"]
}
```

### 5. Check Egress Guard & Privacy Status (Implemented · P1)
```bash
curl -s http://127.0.0.1:8000/api/v1/privacy/status | jq .
```
```json
{
  "egress_guard": {
    "active": true,
    "allowed_hosts": ["127.0.0.1", "::1", "localhost"],
    "blocked_attempts": 0
  },
  "network_mode": "host-loopback",
  "temp_files_created": 0,
  "sessions": 1,
  "retention_ttl_s": 1800
}
```

### 6. Crypto-Shred Session Document (Implemented · P1)
```bash
curl -s -X DELETE http://127.0.0.1:8000/api/v1/documents/doc_e4c5b364817a | jq .
```
```json
{
  "deleted": true,
  "crypto_shredded": true
}
```
Subsequent requests to `GET /api/v1/documents/doc_e4c5b364817a` immediately return `404 NOT_FOUND` because the in-memory AES-256-GCM encryption key was permanently erased.

### 7. Planned Endpoints (Phase 2–4 Stubs)
Calling planned endpoints returns RFC 9457 `501 NOT_IMPLEMENTED`:
```bash
curl -s -X POST http://127.0.0.1:8000/api/v1/documents/doc_test/analyze \
  -H "Content-Type: application/json" -d '{}' | jq .
```
```json
{
  "type": "https://lexishield.local/errors/not-implemented",
  "title": "Not implemented yet",
  "status": 501,
  "code": "NOT_IMPLEMENTED",
  "detail": "This endpoint is scheduled for Phase 2."
}
```

---

## Testing & Benchmark Gates

The repository maintains cumulative testing gates. Running a phase test also verifies all prior phases.

### Run Phase Test Gates

```bash
# Backend API with auto-reload off, loopback only
cd backend

# Phase 0 Gate: Unit & frozen contract tests (no model required)
uv run pytest -m phase0 -q

# Phase 1 Gate: Ingestion, trust boundary, vault & retrieval tests
uv run pytest -m "phase0 or phase1" -q

# Live Gemma Model Gate: Requires Ollama running with target model
uv run pytest -m live -q

# Dependency Telemetry Audit: Fails if Sentry, PostHog, or analytics packages are locked
uv run python scripts/audit_deps.py

# Contract Freshness Check: Verifies openapi.json is in sync with backend routes
uv run python scripts/export_openapi.py --check
```

### Run Live API Smoke Checks

With the server running in another terminal (`uv run lexishield serve`):
```bash
# Phase 0 Smoke Check: 5 checks (health, info, contract paths, problem+json, loopback bind)
uv run python scripts/smoke_api.py --phase 0

# Phase 1 Smoke Check: 11 checks (offset round-trips, hidden injection, failure codes, crypto-shred)
uv run python scripts/smoke_api.py --phase 1
```

### Benchmarks (Verified OMEN Hardware Evidence)

Benchmark trials execute against structured JSON schemas using [`backend/scripts/bench.py`](backend/scripts/bench.py).

Run the benchmark:
```bash
uv run python scripts/bench.py --models gemma4:e4b-it-qat --label omen-rtx5070 --trials 10
```

**Measured Results on HP OMEN (RTX 5070 Laptop GPU, 8 GB VRAM, Windows 11, Intel Core i9):**
*File: [`backend/eval/results/bench_gemma4-e4b-it-qat_omen-rtx5070.json`](backend/eval/results/bench_gemma4-e4b-it-qat_omen-rtx5070.json)*

| Metric | Primary Model (`gemma4:e4b-it-qat`) | Comparison Model (`gemma3n:e4b`) |
|---|---|---|
| **Trials** | 10 | 10 |
| **Schema Valid Rate** | **1.0 (10/10)** | **1.0 (10/10)** |
| **Status Correct Rate** | **1.0 (10/10)** | **1.0 (10/10)** |
| **Quote Verbatim Rate** | **1.0 (10/10)** | **1.0 (10/10)** |
| **Median Generation Speed** | **61.74 tokens/sec** | 48.68 tokens/sec |
| **Median Prompt Ingestion** | **4,171.7 tokens/sec** | 3,452.7 tokens/sec |
| **Median Latency** | **2.73 seconds** | 4.76 seconds |
| **P95 Latency** | **2.95 seconds** | 5.23 seconds |
| **Peak VRAM Allocated** | 4,278.0 MiB | 4,286.0 MiB |

---

## Privacy Architecture & Local Trust Boundary

### The TEE Question Answered Honestly

A hardware Trusted Execution Environment (TEE)—such as Intel SGX/TDX, AMD SEV-SNP, or NVIDIA Confidential Computing—protects data when executing on a third-party server. LexiShield runs **directly on the user's personal hardware**, which is inherently more private because document bytes never cross a network.

Hardware TEE availability analysis on consumer developer hardware:
- **Intel SGX:** Deprecated on client Core CPUs from 11th Gen onward.
- **Intel TDX / AMD SEV-SNP:** Server-class platforms only (Xeon / EPYC).
- **NVIDIA GPU TEE:** Data-center architectures only (Hopper / Blackwell), unavailable on GeForce RTX laptop GPUs.
- **Cloud Confidential VMs:** Strictly forbidden by PS2 rules because private documents cannot be transmitted to external servers.

### The Local Trust Boundary: Isolate · Seal · Attest

LexiShield implements the three core guarantees of a TEE in software:

1. **Isolate (Network & Telemetry Defense):**
   - **In-process Egress Guard:** `sys.addaudithook` monitors `socket.connect`, `socket.getaddrinfo`, and `socket.sendto`, raising `EgressBlocked` for non-loopback connections.
   - **Loopback-Only Binding:** Uvicorn and Ollama bind strictly to `127.0.0.1`.
   - **Dependency Audit:** [`backend/scripts/audit_deps.py`](backend/scripts/audit_deps.py) scans [`backend/uv.lock`](backend/uv.lock) to guarantee zero analytics or crash-reporting libraries (e.g., Sentry, PostHog, Mixpanel).
2. **Seal (Zero Disk Spillage & In-Memory Encryption):**
   - **Sealed Session Vault:** Ephemeral per-session AES-256-GCM encryption keys generated with `os.urandom`. Document text and embeddings remain in RAM and are never persisted to disk.
   - **Temp-File Sentinel:** MultiPartParser spool limit is raised to match the upload limit; tests verify zero temp files written.
   - **Crypto-Shredding:** Invoking `DELETE /api/v1/documents/{id}` or `DELETE /api/v1/sessions` discards the AES key, making memory ciphertext instantly unrecoverable.
3. **Attest (Cryptographic Evidence):**
   - **Signed Privacy Receipts:** Phase 4 exports an Ed25519-signed JSON receipt recording application version, git commit, `uv.lock` SHA-256, model digest, egress stats (`blocked_attempts: 0`), and `temp_files_created: 0`.

---

## Datasets, Models & Licences

| Resource | Scope / Description | Usage in LexiShield | Licence & Terms |
|---|---|---|---|
| **Google Gemma 4** | `gemma4:e4b-it-qat` & `gemma4:e2b-it-qat` | Primary on-device chat and structured classification model | [Gemma Terms of Use](https://ai.google.dev/gemma/terms) |
| **Google EmbeddingGemma** | `embeddinggemma:300m` | Local semantic embeddings for hybrid clause retrieval | [Gemma Terms of Use](https://ai.google.dev/gemma/terms) |
| **CUAD v1** | Atticus Project: 510 commercial legal contracts with 13,000+ annotations | Phase 4 evaluation benchmark (20-contract subset); not committed | CC BY 4.0 (NeurIPS 2021) |
| **Open India Law** | `vaquill/open-india-law` (snapshot v2026.08): Central & State Acts | Offline SQLite FTS5 statute context index (filtered Act list); judgments omitted | Data CC BY 4.0 |
| **India Code** | Central and State legislation portal (`indiacode.gov.in`) | Referenced strictly via user-facing canonical source URLs; no scraping or redistribution | Official Government Portal |
| **Synthetic Fixtures** | Custom test agreements in [`backend/tests/fixtures/`](backend/tests/fixtures/) | Unit tests, contract validation, and golden benchmark keys | Apache-2.0 (LexiShield Team) |

---

## Repository Structure

```
Geeks/
├── LICENSE                        # Apache License 2.0
├── NOTICE                         # Dataset, model, and attribution disclosures
├── README.md                      # This comprehensive documentation
├── contracts/                     # Frozen API contract v1 for frontend development
│   ├── openapi.json               # Full OpenAPI 3.1 schema specification
│   ├── README.md                  # Frontend development rules and schema mapping
│   └── examples/                  # Realistic JSON response fixtures for UI mocking
├── docs/                          # Architecture, project log, and runbooks
│   ├── IMPLEMENTATION_PLAN.md     # Working phase checklist and test criteria
│   ├── PROJECT_LOG.md             # Project status, architectural decisions, and findings
│   ├── OMEN_HANDOFF.md            # Hardware setup and development handoff
│   ├── omen-setup.md              # Windows / PowerShell runbook
│   └── plan/
│       └── LexiShield_Build_Plan.docx # Master architectural source of truth
├── backend/                       # Python 3.12 FastAPI service (uv workspace)
│   ├── pyproject.toml             # Project manifest and locked dependencies
│   ├── uv.lock                    # Cryptographically pinned lockfile
│   ├── config/
│   │   └── lexishield.yaml        # Runtime configuration (models, limits, privacy)
│   ├── eval/results/              # Hardware benchmark outputs (JSON)
│   ├── scripts/                   # Benchmarking, smoke tests, OpenAPI export, dependency audit
│   │   ├── audit_deps.py          # Banned telemetry checker
│   │   ├── bench.py               # Speed, RAM/VRAM, and accuracy benchmark
│   │   ├── contract_examples.py   # Generates contract fixtures from Pydantic models
│   │   ├── export_openapi.py      # Generates and validates openapi.json
│   │   ├── make_fixtures.py       # Builds synthetic test PDFs and attack variants
│   │   └── smoke_api.py           # Multi-phase live API smoke tests
│   ├── src/lexishield/            # Core backend package
│   │   ├── api/                   # FastAPI app, RFC 9457 errors, upload limits, routers
│   │   ├── ingest/                # Parsers (PDF, DOCX, TXT), offset maps, hidden text scan
│   │   ├── llm/                   # LLMGateway: single choke-point for Gemma via Ollama
│   │   ├── models/                # Domain models (domain.py) and API schemas (api.py)
│   │   ├── retrieval/             # BM25 + EmbeddingGemma hybrid retrieval & RRF
│   │   ├── trust/                 # Egress guard, AES-GCM vault, temp-file sentinel
│   │   ├── settings.py            # Typed settings via pydantic-settings
│   │   └── cli.py                 # CLI interface (lexishield serve | info)
│   └── tests/                     # Test suite (phase markers: phase0, phase1, live)
└── frontend/                      # React frontend interface (built against contracts/)
```

---

## Troubleshooting & Known Limitations

1. **Non-Loopback Host Rejection:**
   If the server is started with `--host 0.0.0.0` or a remote IP, it will immediately exit with:
   `Refusing to bind a non-loopback address: LexiShield must stay on-device.`  
   *Fix:* Bind only to `127.0.0.1`, `localhost`, or `::1`.
2. **Missing Ollama Model (`models_ready: false`):**
   If `GET /api/v1/health` reports missing models, check `ollama list`. The model tag must match the active profile in `config/lexishield.yaml` (e.g., `gemma4:e4b-it-qat`).
3. **Scanned Documents (OCR Disabled):**
   Uploading a scanned image PDF returns `422 SCANNED_NO_TEXT`. Optical Character Recognition (`features.ocr`) is disabled by default to keep the local runtime lightweight. Upload text-based PDFs, DOCX, or pasted text.
4. **Local Host Malware / Root Attackers:**
   While LexiShield prevents outbound network leakage and wipes memory on exit, it cannot defend against an attacker with root/admin access on the local host. Full-disk encryption (BitLocker or LUKS) is strongly recommended.
5. **Windows PowerShell Environment Variables:**
   Use `$env:LEXISHIELD_MODELS__PROFILE="cpu"` in PowerShell rather than Bash syntax.
