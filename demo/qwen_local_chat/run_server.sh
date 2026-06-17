#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")"

MODEL="models/qwen2.5-0.5b-instruct-q4_k_m.gguf"

if ! command -v llama-server >/dev/null 2>&1; then
  echo "llama-server not found. Install with: brew install llama.cpp" >&2
  exit 1
fi

if [ ! -f "$MODEL" ]; then
  echo "model not found: $MODEL" >&2
  exit 1
fi

exec llama-server \
  -m "$MODEL" \
  --host 127.0.0.1 \
  --port 8767 \
  -c 2048
