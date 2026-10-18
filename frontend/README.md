# LexiShield frontend (React + Vite + Tailwind)

The web app for LexiShield. It talks only to the local backend, through the relative path `/api/v1`.

## Run

- **With the backend (normal use):** `npm run build`, then start the backend (`run.ps1` / `run.sh` at the repo root,
  or `uv run lexishield serve` in `backend/`). The backend serves this app at http://127.0.0.1:8000.
- **Development with hot reload:** start the backend, then `npm run dev` here and open http://localhost:5173.
  Vite forwards `/api` to `http://127.0.0.1:8000` (see `vite.config.js`).
- **Demo mode without a backend:** `VITE_USE_MOCKS=true npm run dev` shows the contract fixtures from
  `src/api/mockData.js`. Never use demo mode with a real document: fixture answers are not about it.

## Rules that protect privacy and grounding

- Bundle **all** assets locally: no CDNs, web fonts, analytics, error trackers or remote images. The app must work
  with the network off.
- Show quotes only from `citations[].quote` / `source.quote` (the document's own text). Label citations with
  `page`, `line_start`-`line_end` (`src/lib/format.js`).
- Opening a citation highlights `[char_start, char_end)` in that page's text from `GET /documents/{id}`;
  "Open original" uses `GET /documents/{id}/file` (`#page=N` for PDFs).
- Show real errors. A failed call must never fall back to fixture data outside demo mode (`src/api/client.js`).
- Never hide "document silent" (`NOT_MENTIONED`) items; keep the "Preliminary information, not legal advice" footer.

The full API contract and rendering guide: [`../contracts/README.md`](../contracts/README.md).
