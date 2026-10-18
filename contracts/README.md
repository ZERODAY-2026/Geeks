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
| scenarios.json | GET /scenarios |
| scenario_result.json | POST /documents/{id}/scenarios/{sid}/run |
| statutes.json | GET /documents/{id}/statutes |
| brief.json | GET /documents/{id}/brief?format=json |
| packs.json | GET /packs |
| error_scanned.json | any error (problem+json) |

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
