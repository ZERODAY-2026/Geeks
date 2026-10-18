<#
Starts LexiShield on Windows, fully offline. Run install.ps1 once first.

    powershell -ExecutionPolicy Bypass -File .\run.ps1

It starts Ollama if it is not running, loads Gemma into GPU memory, starts the server on http://127.0.0.1:8000
(loopback only) and opens the app in your browser. Press Ctrl+C to stop the server.
#>
$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $MyInvocation.MyCommand.Path
$ChatModel = "gemma4:e4b-it-qat"
$OllamaUrl = "http://127.0.0.1:11434"
$AppUrl = "http://127.0.0.1:8000"

function OllamaUp {
    try { Invoke-RestMethod "$OllamaUrl/api/version" -TimeoutSec 2 | Out-Null; return $true } catch { return $false }
}

# Nothing below needs the internet; tell uv not to try.
$env:UV_OFFLINE = "1"
$env:LEXISHIELD_MODELS__PROFILE = "gpu"
if (-not (Get-Command uv -ErrorAction SilentlyContinue)) { $env:Path = "$env:USERPROFILE\.local\bin;$env:Path" }

if (-not (Test-Path "$Root\frontend\dist\index.html")) {
    Write-Host "The web app is not built. Run install.ps1 first." -ForegroundColor Red
    exit 1
}

if (-not (OllamaUp)) {
    Write-Host "Starting Ollama..."
    Start-Process ollama -ArgumentList "serve" -WindowStyle Hidden
    for ($i = 0; $i -lt 30 -and -not (OllamaUp); $i++) { Start-Sleep -Seconds 1 }
    if (-not (OllamaUp)) { Write-Host "Ollama did not start. Run 'ollama serve' and check its output." -ForegroundColor Red; exit 1 }
}

Write-Host "Loading Gemma into GPU memory (first time takes a few seconds)..."
try {
    $body = @{ model = $ChatModel; keep_alive = "30m" } | ConvertTo-Json
    Invoke-RestMethod -Method Post "$OllamaUrl/api/generate" -Body $body -ContentType "application/json" -TimeoutSec 180 | Out-Null
} catch {
    Write-Host "Could not load $ChatModel. Is it pulled? Run install.ps1." -ForegroundColor Red
    exit 1
}

# Open the browser once the server answers.
Start-Job -ScriptBlock {
    param($url)
    for ($i = 0; $i -lt 60; $i++) {
        try { Invoke-RestMethod "$url/api/v1/health" -TimeoutSec 2 | Out-Null; Start-Process $url; return } catch { Start-Sleep -Seconds 1 }
    }
} -ArgumentList $AppUrl | Out-Null

Write-Host "Starting LexiShield on $AppUrl (Ctrl+C to stop)" -ForegroundColor Green
Set-Location "$Root\backend"
uv run --frozen lexishield serve
