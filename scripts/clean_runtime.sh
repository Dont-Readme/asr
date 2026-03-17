#!/usr/bin/env bash
set -euo pipefail

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

clean_dir() {
  local dir_path="$1"

  if [[ ! -d "$dir_path" ]]; then
    echo "skip: $dir_path (directory not found)"
    return 0
  fi

  find "$dir_path" -mindepth 1 ! -name '.gitkeep' -print -delete
}

echo "Cleaning runtime artifacts under: $PROJECT_ROOT"
clean_dir "$PROJECT_ROOT/work"
clean_dir "$PROJECT_ROOT/output"
clean_dir "$PROJECT_ROOT/logs"

echo "Done."
