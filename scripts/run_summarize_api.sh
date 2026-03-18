#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
HOST="${HOST:-0.0.0.0}"
PORT="${PORT:-8093}"

cd "$ROOT_DIR"
uv run asr-summarize-api --host "$HOST" --port "$PORT"
