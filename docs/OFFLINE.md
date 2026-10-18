# Running LexiShield fully offline

LexiShield runs with no internet connection. Everything it needs is installed once, while the machine is still online.
After that, unplug the network: the app, the model and the analysis all run on this machine.

The quickest path: `install.ps1` / `install.sh` (once, online), then `run.ps1` / `run.sh` (offline). The steps
below are what those scripts do.

## 1. One-time set-up (online)

```powershell
cd backend
uv sync --frozen                                   # Python packages into .venv
ollama pull gemma4:e4b-it-qat                      # chat model (gpu profile)
ollama pull embeddinggemma:300m                    # embedding model
uv run python scripts/prepare_offline.py           # NLTK cmudict into data/nltk_data; checks the models are present
```

`prepare_offline.py` must end with `ready for offline use`.

Optional, also online and only once:
- Statute context: build `data/statutes.sqlite` with `scripts/build_statute_index.py` (needs Open India Law access).
  Without it the app works and the statutes endpoint says the index is not installed.
- CUAD evaluation data: `scripts/fetch_cuad_eval.py`. Evaluation only; never needed to run the app.

## 2. Running (offline)

```powershell
ollama serve                                       # in its own terminal; quit the Ollama tray app (it checks for updates)
cd backend
$env:UV_OFFLINE = "1"                              # uv never tries to download anything
uv run --frozen lexishield serve                   # http://127.0.0.1:8000, loopback only
```

`OLLAMA_HOST` must be unset or `127.0.0.1:11434`.

## 3. What keeps it offline

| Risk | Control |
|---|---|
| Any library opening a network connection | The egress guard (a Python audit hook) refuses every non-loopback connection and DNS lookup inside the server, and counts them in `/privacy/status`. |
| The reading grade downloading NLTK data | The data is installed at set-up time. If it is missing, the grade is left empty; the app never downloads it. |
| The `/docs` page loading Swagger UI from a CDN | `/docs` is off (`server.api_docs: false`). The contract is local: `contracts/openapi.json`. |
| `uv` re-syncing packages at start | `UV_OFFLINE=1` and `--frozen`. |
| The model runtime | Ollama on 127.0.0.1 with models already pulled. Run `ollama serve`, not the tray app. |
| The frontend | Bundle every asset locally: no fonts, CDNs, analytics or remote images (see `contracts/README.md`). |

## 4. Set-up scripts that need the network

`fetch_cuad_eval.py`, `build_statute_index.py` (when downloading its parquet files) and `prepare_offline.py` use the
network on purpose. They are set-up tools and are never called by the running app.
