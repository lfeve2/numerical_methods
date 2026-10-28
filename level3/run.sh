#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$ROOT_DIR"

CODE_FILE="code/level3_phase_change.c"
OUT_DIR="output"

mkdir -p "$OUT_DIR"

if [ ! -f "$CODE_FILE" ]; then
  echo "No Level 3 solver is currently present in $ROOT_DIR/code/."
  echo "Add your Basilisk C file as level3_phase_change.c before running this script."
  exit 1
fi

if ! command -v qcc >/dev/null 2>&1; then
  echo "qcc was not found on your PATH. Install Basilisk and make sure qcc is visible."
  exit 1
fi

qcc -O2 -Wall -disable-dimensions "$CODE_FILE" -o "$OUT_DIR/level3_phase_change" -lm
exec "$OUT_DIR/level3_phase_change" "${@:-9 50.0 4.0 1.0 0.60 collapse_total}"
