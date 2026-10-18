# HP OMEN (Windows, RTX 5070) runbook: inference host and demo machine

Run these in **PowerShell**. Steps 1–3 are set-up time (network allowed). Everything after runs offline.

## 1. Install tools
```powershell
# uv (Python manager; installs Python 3.12 for the project)
powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
# Ollama for Windows: https://ollama.com/download  (0.40+), then check:
ollama --version
nvidia-smi        # driver must show the RTX 5070
```

## 2. Pull the models (gpu profile + the 'preferred class' comparison)
```powershell
ollama pull gemma4:e4b-it-qat
ollama pull embeddinggemma:300m
ollama pull gemma3n:e4b          # optional: for the Gemma 3n benchmark row
```

## 3. Get the code
```powershell
git clone https://github.com/ZERODAY-2026/Geeks.git
cd Geeks\backend
uv sync --frozen
```

## 4. Phase 0 gate on the OMEN
```powershell
uv run pytest -m phase0 -q                       # includes the live test (gpu profile is the default)
uv run python scripts\bench.py --models gemma4:e4b-it-qat gemma3n:e4b --label omen-rtx5070 --trials 10
uv run lexishield serve                          # terminal 1
uv run python scripts\smoke_api.py --phase 0     # terminal 2
```
Commit the `backend\eval\results\bench_*_omen-rtx5070.json` files. They feed `GET /system/benchmark` and
the memory/speed report PS2 requires.

**Check that the GPU is actually used:** run `nvidia-smi` during the benchmark. Ollama's memory usage should
show and VRAM should be about 6–7 GB. If Ollama falls back to CPU, update the NVIDIA driver and Ollama
(the RTX 50-series needs recent builds). If it still fails, keep working on CPU (`--profile cpu` uses
gemma4:e2b-it-qat) and fix the GPU in parallel.

## 5. Demo hygiene (privacy gate)
- Quit the Ollama **tray app** and run `ollama serve` in a terminal instead. The desktop app can check
  for updates in the background, and that call must not be running during processing.
- Make sure `OLLAMA_HOST` is unset or `127.0.0.1:11434` (never `0.0.0.0`).
- For the recorded demo: turn off Wi-Fi and unplug Ethernet, then run the full flow (Phase 6 script).
- Serving the team over the LAN (`OLLAMA_HOST=0.0.0.0`) is a **development-only** convenience for
  synthetic documents. Turn it off before any demo or real document.
