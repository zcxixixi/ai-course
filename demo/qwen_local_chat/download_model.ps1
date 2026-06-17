$ErrorActionPreference = "Stop"

$Root = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $Root

$ModelDir = "models"
$ModelFile = Join-Path $ModelDir "qwen2.5-0.5b-instruct-q4_k_m.gguf"
$ModelUrl = "https://huggingface.co/Qwen/Qwen2.5-0.5B-Instruct-GGUF/resolve/main/qwen2.5-0.5b-instruct-q4_k_m.gguf"

New-Item -ItemType Directory -Force -Path $ModelDir | Out-Null

if (Test-Path $ModelFile) {
  Write-Host "model already exists: $ModelFile"
  exit 0
}

Write-Host "downloading model to: $ModelFile"
Invoke-WebRequest -Uri $ModelUrl -OutFile $ModelFile
Write-Host "done"
