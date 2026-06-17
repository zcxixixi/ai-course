$ErrorActionPreference = "Stop"

$Root = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $Root

if (-not (Get-Command winget -ErrorAction SilentlyContinue)) {
  throw "winget not found. Install App Installer from Microsoft Store, then rerun this script."
}

if (-not (Get-Command llama-server -ErrorAction SilentlyContinue)) {
  winget install -e --id ggml.llamacpp --accept-package-agreements --accept-source-agreements
} else {
  Write-Host "llama.cpp already installed"
}

& "$Root\download_model.ps1"

Write-Host ""
Write-Host "ready. start server with:"
Write-Host "  .\run_server.ps1"
