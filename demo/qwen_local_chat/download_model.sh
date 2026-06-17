#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")"

MODEL_DIR="models"
MODEL_FILE="$MODEL_DIR/qwen2.5-0.5b-instruct-q4_k_m.gguf"
MODEL_URL="https://huggingface.co/Qwen/Qwen2.5-0.5B-Instruct-GGUF/resolve/main/qwen2.5-0.5b-instruct-q4_k_m.gguf"

mkdir -p "$MODEL_DIR"

if [ -f "$MODEL_FILE" ]; then
  echo "model already exists: $MODEL_FILE"
  exit 0
fi

echo "downloading model to: $MODEL_FILE"
curl -L --fail --continue-at - --output "$MODEL_FILE" "$MODEL_URL"
echo "done"
