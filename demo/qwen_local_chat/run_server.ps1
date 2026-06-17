$ErrorActionPreference = "Stop"

$Root = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $Root

$Model = "models\qwen2.5-0.5b-instruct-q4_k_m.gguf"

if (-not (Get-Command llama-server -ErrorAction SilentlyContinue)) {
  throw "llama-server not found. Run .\setup_windows.ps1 first."
}

if (-not (Test-Path $Model)) {
  throw "model not found: $Model. Run .\download_model.ps1 first."
}

llama-server `
  -m $Model `
  --host 127.0.0.1 `
  --port 8767 `
  -c 2048
