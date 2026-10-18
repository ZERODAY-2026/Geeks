#!/usr/bin/env bash
# LexiShield installer for Linux with an NVIDIA GPU. Run it once, while online:
#
#     bash install.sh
#
# It checks the NVIDIA GPU, Ollama and Node.js, installs uv if missing, installs the Python backend from the
# lockfile, downloads the Gemma models, prepares the offline data and builds the web app. After it finishes, nothing
# needs the internet: start the app with `bash run.sh`. (macOS is not supported: an NVIDIA GPU is required.)
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CHAT_MODEL="gemma4:e4b-it-qat"
EMBED_MODEL="embeddinggemma:300m"
OLLAMA_URL="http://127.0.0.1:11434"

step() { printf '\n\033[36m==> %s\033[0m\n' "$1"; }
fail() { printf '\n\033[31mERROR: %s\033[0m\n' "$1"; exit 1; }
ollama_up() { curl -sf "$OLLAMA_URL/api/version" >/dev/null 2>&1; }

step "Checking the GPU (an NVIDIA GPU with at least 8 GB of memory is required)"
command -v nvidia-smi >/dev/null || fail "nvidia-smi was not found. Install the NVIDIA driver, then run this installer again."
VRAM="$(nvidia-smi --query-gpu=memory.total --format=csv,noheader,nounits | head -n1 | tr -d ' ')"
GPU="$(nvidia-smi --query-gpu=name --format=csv,noheader | head -n1)"
[ "$VRAM" -ge 7500 ] || fail "$GPU has $VRAM MiB of memory; $CHAT_MODEL needs at least 8 GB."
echo "    $GPU, $VRAM MiB"

step "Checking Ollama (runs Gemma locally)"
command -v ollama >/dev/null || fail "Ollama is not installed. Install it from https://ollama.com/download, then run this installer again."
echo "    $(ollama --version)"

step "Checking Node.js 18 or newer (builds the web app)"
command -v node >/dev/null || fail "Node.js is not installed. Install the LTS version from https://nodejs.org, then run this installer again."
NODE_MAJOR="$(node -v | sed 's/^v//' | cut -d. -f1)"
[ "$NODE_MAJOR" -ge 18 ] || fail "Node.js $(node -v) is too old; version 18 or newer is needed."
echo "    node $(node -v)"

step "Checking uv (installs Python 3.12 and the backend packages)"
if ! command -v uv >/dev/null; then
  echo "    uv not found; installing it"
  curl -LsSf https://astral.sh/uv/install.sh | sh
  export PATH="$HOME/.local/bin:$PATH"
  command -v uv >/dev/null || fail "uv could not be installed. See https://docs.astral.sh/uv/."
fi
echo "    $(uv --version)"

step "Installing the backend (exact versions from backend/uv.lock)"
(cd "$ROOT/backend" && uv sync --frozen)

step "Starting Ollama"
if ! ollama_up; then
  nohup ollama serve >/tmp/lexishield-ollama.log 2>&1 &
  for _ in $(seq 1 30); do ollama_up && break; sleep 1; done
  ollama_up || fail "Ollama did not start. See /tmp/lexishield-ollama.log."
fi
echo "    Ollama is running on $OLLAMA_URL"

step "Downloading the models (about 6.7 GB, one time)"
ollama pull "$CHAT_MODEL"
ollama pull "$EMBED_MODEL"

step "Preparing offline data and checking the models"
(cd "$ROOT/backend" && uv run --frozen python scripts/prepare_offline.py)

step "Building the web app"
(cd "$ROOT/frontend" && npm ci --no-audit --no-fund && npm run build)

printf '\n\033[32mLexiShield is installed. You can now disconnect from the internet.\033[0m\n'
echo "Start it with:  bash run.sh"
