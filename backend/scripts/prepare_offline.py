"""One-time set-up for offline use. Run this while the machine still has internet; after it, nothing needs a network.

It installs NLTK's cmudict (used for the reading grade) into backend/data/nltk_data, which git ignores, and checks
that Ollama on loopback already has every configured model. It does not download models: pull them with
`ollama pull <name>` first.

Usage:  uv run python scripts/prepare_offline.py
"""

from __future__ import annotations

import sys

import httpx
import nltk

from lexishield.settings import BACKEND_DIR, get_settings

NLTK_DIR = BACKEND_DIR / "data" / "nltk_data"


def main() -> int:
    ok = True
    NLTK_DIR.mkdir(parents=True, exist_ok=True)
    if nltk.download("cmudict", download_dir=str(NLTK_DIR), quiet=True):
        print(f"cmudict installed in {NLTK_DIR}")
    else:
        print("cmudict download failed: the reading grade will be left empty offline", file=sys.stderr)
        ok = False

    cfg = get_settings()
    wanted = {cfg.models.active.chat, cfg.models.active.embed}
    try:
        installed = {m["name"] for m in httpx.get(f"{cfg.ollama.host}/api/tags", timeout=5).json().get("models", [])}
    except httpx.HTTPError:
        print(f"Ollama is not reachable at {cfg.ollama.host}; start it with `ollama serve`", file=sys.stderr)
        return 1
    for name in sorted(wanted):
        full = name if ":" in name else f"{name}:latest"
        if full in installed:
            print(f"model present: {full}")
        else:
            print(f"model missing: {full} (run: ollama pull {full})", file=sys.stderr)
            ok = False
    print("ready for offline use" if ok else "not ready: fix the items above while online")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
