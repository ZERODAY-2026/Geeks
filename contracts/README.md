# LexiShield API contract (frontend hand-off)

- **Spec:** `openapi.json` (OpenAPI 3.1). Generate a typed client, e.g. `npx openapi-typescript contracts/openapi.json -o src/api/schema.d.ts`.
- **Examples:** `examples/*.json` hold one realistic payload per response type, built from the backend's
  Pydantic models (synthetic document). Develop the UI against these until the endpoints are live.
- **Base URL:** `http://127.0.0.1:8000/api/v1`. CORS allows `http://localhost:5173`, `http://127.0.0.1:5173`
  and `http://localhost:3000` (configurable in `backend/config/lexishield.yaml`).
- **Regenerate** after backend model or route changes: `cd backend && uv run python scripts/export_openapi.py`.
  The test suite fails if these files are stale.

## Freeze rules
Contract v1 is frozen at the end of Phase 0. After that, changes are **additive only** (new optional fields or
new endpoints). Endpoints not built yet return `501` with `code: NOT_IMPLEMENTED` and the delivering phase
in `detail`.

## Example → endpoint map

| Example file | Endpoint |
|---|---|
| health.json | GET /health |
| system_info.json | GET /system/info |
| benchmark.json | GET /system/benchmark |
| privacy_status.json | GET /privacy/status |
| privacy_receipt.json | POST /privacy/receipts |
| document_summary.json | POST /documents, POST /documents/text |
| document_detail.json | GET /documents/{id} |
| job_accepted.json | POST /documents/{id}/analyze |
| job_info.json | GET /jobs/{job_id} |
| card.json, checklist_item_silent.json | SSE `card.ready` / `checklist.item` payloads |
| report.json | GET /documents/{id}/report |
| ask_answered.json, ask_declined.json, ask_not_in_document.json | POST /documents/{id}/ask |
| (binary, no example) | GET /documents/{id}/file |
| scenarios.json | GET /scenarios |
| scenario_result.json | POST /documents/{id}/scenarios/{sid}/run |
| statutes.json | GET /documents/{id}/statutes |
| brief.json | GET /documents/{id}/brief?format=json |
| packs.json | GET /packs |
| error_scanned.json | any error (problem+json) |

`report.json`, `card.json`, `checklist_item_silent.json` and the three `ask_*.json` files are real output, captured
from the backend on the synthetic rental fixture (`backend/scripts/capture_examples.py`), not hand-written.

## Chat: upload, then ask (`POST /documents/{id}/ask`)
1. `POST /documents` (multipart field `file`: PDF, DOCX or TXT) or `POST /documents/text`. Keep `document_id`.
2. For each chat message: `POST /documents/{id}/ask` with `{"question": "...", "conversation_id": <from the last reply>}`.
   Each message is answered on its own and is fully grounded; `conversation_id` only groups the thread in the UI.
   Running `POST /documents/{id}/analyze` first is optional for Ask (it adds party roles), and required for scenarios
   and the brief.
3. Render by `status`:

| status | Show |
|---|---|
| `ANSWERED` / `PARTIAL` | Each `claims[].text`, each with its citation chips. `PARTIAL` means part of the answer was removed. |
| `NOT_IN_DOCUMENT` | `message` and `not_found_note`, then `related_clauses` as "closest clauses" (never as an answer). |
| `LEGAL_VERDICT_DECLINED` | `message`, `related_clauses`, and the `escalation` card (who can help, free help, urgency). |
| `NEEDS_CLARIFICATION` | `clarifying_question`. |
| `OUT_OF_SCOPE` | `message`. |

Always show `disclaimer`. Never show text that is not in `claims`, `message` or a citation.

## Opening a citation in the document
Every citation (`claims[].citations[]`, `related_clauses[]`, `evidence[]`, `source`) has:
`page`, `line_start`, `line_end` (1-based, counted within that page), `char_start` / `char_end` (offsets into the whole
document text), `clause_id`, and `quote` (the exact source text).

Get the original file from `GET /documents/{id}/file` (same `Content-Type` as the upload) and the extracted text from
`GET /documents/{id}` (`pages[].text`, each with its own `char_start`).

- **PDF:** render the file with pdf.js (`pdfjs-dist`, bundled locally including its worker; no CDN). Open `page`,
  find `quote` in that page's text layer and highlight it; scroll to `line_start` if the text-layer match fails.
- **TXT:** render `pages[0].text` and highlight `[char_start - page.char_start, char_end - page.char_start)`.
  Use the extracted text, not the raw file: the offsets are into the extracted text.
- **DOCX:** browsers cannot display DOCX. Render `pages[0].text` the same way as TXT and highlight by offsets.
  Offer the original file as a download. (Rendering the DOCX itself, e.g. with `docx-preview` bundled locally, is
  optional; if you do it, highlight by searching for `quote`.)

Chip label: `p. {page}, lines {line_start}-{line_end}` (or `line {line_start}` when they are equal).

## SSE stream: `GET /jobs/{job_id}/events`
Events, in order: `job.stage` (JobProgress) → `classification.ready` ({classification, jurisdiction}) →
`checklist.item` (ChecklistItem) and `card.ready` (ClauseCard), repeated → `report.ready`
({document_id, report_url}). `warning` (IngestionWarning) can appear at any point; `job.failed` (Problem) ends the stream on error.

## UI rules that protect the privacy gate and the scoring
1. **Bundle every asset locally:** no Google Fonts, CDNs, analytics, error trackers or remote images.
   One remote request breaks the "nothing leaves the device" gate.
2. Render quotes **only** from `source.quote` / `citations[].quote`. Highlight with `char_start`/`char_end`
   against the page text from `GET /documents/{id}` (offsets are document-global; subtract `page.char_start`).
3. Show the tier badge (`STATED` / `INTERPRETATION` / `NOT_FOUND` / `ASK_A_LAWYER`) and the distortion badge
   on every card. When `plain_explanation` is null, show `explanation_withheld_reason` and the source quote.
4. Never hide `NOT_MENTIONED` checklist items. They are a feature ("the document is silent on…").
5. Keep a persistent footer: "Preliminary information, not legal advice." Add a Trust page fed by
   `/privacy/status`, `/system/info`, `/system/benchmark` and `/eval/summary`.
