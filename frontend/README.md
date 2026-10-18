# LexiShield frontend (React)

Built separately (Antigravity) against the frozen contract in [`../contracts`](../contracts/README.md).

Requirements that protect the PS2 privacy gate:
- Bundle **all** assets locally: no CDNs, Google Fonts, analytics, error trackers or remote images.
- API base URL: `http://127.0.0.1:8000/api/v1`. Dev server on port 5173 or 3000 (already allowed by CORS).
- Render quotes only from `source.quote` / `citations[].quote`; show tier and distortion badges; never hide
  `NOT_MENTIONED` items; keep a "Preliminary information, not legal advice" footer.
