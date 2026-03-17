#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
HOST="${HOST:-0.0.0.0}"
PORT="${PORT:-8092}"
CUDA_DEVICE="${CUDA_DEVICE:-1}"

cd "$ROOT_DIR"
env CUDA_VISIBLE_DEVICES="$CUDA_DEVICE" uv run asr-diarize-api --host "$HOST" --port "$PORT"
