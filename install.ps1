<#
LexiShield installer for Windows. Run it once, while online:

    powershell -ExecutionPolicy Bypass -File .\install.ps1

It checks the NVIDIA GPU, Ollama and Node.js, installs uv if missing, installs the Python backend from the lockfile,
downloads the Gemma models, prepares the offline data and builds the web app. After it finishes, nothing needs the
internet: start the app with .\run.ps1.
#>
$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $MyInvocation.MyCommand.Path
$ChatModel = "gemma4:e4b-it-qat"
$EmbedModel = "embeddinggemma:300m"
$OllamaUrl = "http://127.0.0.1:11434"

function Step($msg) { Write-Host "`n==> $msg" -ForegroundColor Cyan }
function Fail($msg) { Write-Host "`nERROR: $msg" -ForegroundColor Red; exit 1 }
function Run($what, [scriptblock]$cmd) {
    & $cmd
    if ($LASTEXITCODE -ne 0) { Fail "$what failed (exit code $LASTEXITCODE)." }
}
function OllamaUp {
    try { Invoke-RestMethod "$OllamaUrl/api/version" -TimeoutSec 2 | Out-Null; return $true } catch { return $false }
}

Step "Checking the GPU (an NVIDIA GPU with at least 8 GB of memory is required)"
if (-not (Get-Command nvidia-smi -ErrorAction SilentlyContinue)) {
    Fail "nvidia-smi was not found. Install the NVIDIA driver, then run this installer again."
}
$vram = [int]((nvidia-smi --query-gpu=memory.total --format=csv,noheader,nounits | Select-Object -First 1).Trim())
$gpu = (nvidia-smi --query-gpu=name --format=csv,noheader | Select-Object -First 1).Trim()
if ($vram -lt 7500) { Fail "$gpu has $vram MiB of memory; $ChatModel needs at least 8 GB." }
Write-Host "    $gpu, $vram MiB"

Step "Checking Ollama (runs Gemma locally)"
if (-not (Get-Command ollama -ErrorAction SilentlyContinue)) {
    Fail "Ollama is not installed. Install it from https://ollama.com/download, then run this installer again."
}
Write-Host "    $(ollama --version)"

Step "Checking Node.js 18 or newer (builds the web app)"
if (-not (Get-Command node -ErrorAction SilentlyContinue)) {
    Fail "Node.js is not installed. Install the LTS version from https://nodejs.org, then run this installer again."
}
$nodeMajor = [int]((node -v).TrimStart("v").Split(".")[0])
if ($nodeMajor -lt 18) { Fail "Node.js $(node -v) is too old; version 18 or newer is needed." }
Write-Host "    node $(node -v)"

Step "Checking uv (installs Python 3.12 and the backend packages)"
if (-not (Get-Command uv -ErrorAction SilentlyContinue)) {
    Write-Host "    uv not found; installing it"
    powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
    $env:Path = "$env:USERPROFILE\.local\bin;$env:Path"
    if (-not (Get-Command uv -ErrorAction SilentlyContinue)) { Fail "uv could not be installed. See https://docs.astral.sh/uv/." }
}
Write-Host "    $(uv --version)"

Step "Installing the backend (exact versions from backend/uv.lock)"
Push-Location "$Root\backend"
Run "uv sync" { uv sync --frozen }
Pop-Location

Step "Starting Ollama"
if (-not (OllamaUp)) {
    Start-Process ollama -ArgumentList "serve" -WindowStyle Hidden
    for ($i = 0; $i -lt 30 -and -not (OllamaUp); $i++) { Start-Sleep -Seconds 1 }
    if (-not (OllamaUp)) { Fail "Ollama did not start. Run 'ollama serve' in a terminal and check its output." }
}
Write-Host "    Ollama is running on $OllamaUrl"

Step "Downloading the models (about 6.7 GB, one time)"
Run "ollama pull $ChatModel" { ollama pull $ChatModel }
Run "ollama pull $EmbedModel" { ollama pull $EmbedModel }

Step "Preparing offline data and checking the models"
Push-Location "$Root\backend"
Run "prepare_offline.py" { uv run --frozen python scripts/prepare_offline.py }
Pop-Location

Step "Building the web app"
Push-Location "$Root\frontend"
Run "npm ci" { npm ci --no-audit --no-fund }
Run "npm run build" { npm run build }
Pop-Location

Write-Host "`nLexiShield is installed. You can now disconnect from the internet." -ForegroundColor Green
Write-Host "Start it with:  powershell -ExecutionPolicy Bypass -File .\run.ps1"
