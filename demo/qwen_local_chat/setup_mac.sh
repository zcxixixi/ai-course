#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")"

if ! command -v brew >/dev/null 2>&1; then
  echo "Homebrew not found. Install Homebrew first: https://brew.sh" >&2
  exit 1
fi

if ! command -v llama-server >/dev/null 2>&1; then
  brew install llama.cpp
else
  echo "llama.cpp already installed"
fi

./download_model.sh

echo
echo "ready. start server with:"
echo "  ./run_server.sh"
