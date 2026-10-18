#!/usr/bin/env bash
# Starts LexiShield on Linux, fully offline. Run install.sh once first.
#
#     bash run.sh
#
# It starts Ollama if it is not running, loads Gemma into GPU memory, starts the server on http://127.0.0.1:8000
# (loopback only) and opens the app in your browser. Press Ctrl+C to stop the server.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CHAT_MODEL="gemma4:e4b-it-qat"
OLLAMA_URL="http://127.0.0.1:11434"
APP_URL="http://127.0.0.1:8000"

ollama_up() { curl -sf "$OLLAMA_URL/api/version" >/dev/null 2>&1; }

# Nothing below needs the internet; tell uv not to try.
export UV_OFFLINE=1
export LEXISHIELD_MODELS__PROFILE=gpu
export PATH="$HOME/.local/bin:$PATH"

[ -f "$ROOT/frontend/dist/index.html" ] || { echo "The web app is not built. Run install.sh first."; exit 1; }

if ! ollama_up; then
  echo "Starting Ollama..."
  nohup ollama serve >/tmp/lexishield-ollama.log 2>&1 &
  for _ in $(seq 1 30); do ollama_up && break; sleep 1; done
  ollama_up || { echo "Ollama did not start. See /tmp/lexishield-ollama.log."; exit 1; }
fi

echo "Loading Gemma into GPU memory (first time takes a few seconds)..."
curl -sf "$OLLAMA_URL/api/generate" -d "{\"model\": \"$CHAT_MODEL\", \"keep_alive\": \"30m\"}" >/dev/null \
  || { echo "Could not load $CHAT_MODEL. Is it pulled? Run install.sh."; exit 1; }

# Open the browser once the server answers.
(
  for _ in $(seq 1 60); do
    if curl -sf "$APP_URL/api/v1/health" >/dev/null 2>&1; then
      (xdg-open "$APP_URL" || open "$APP_URL") >/dev/null 2>&1 || true
      exit 0
    fi
    sleep 1
  done
) &

echo "Starting LexiShield on $APP_URL (Ctrl+C to stop)"
cd "$ROOT/backend"
exec uv run --frozen lexishield serve
