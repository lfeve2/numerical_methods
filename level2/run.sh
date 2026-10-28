#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$ROOT_DIR"

CODE_FILE="code/level2_thermal.c"
OUT_DIR="output"

mkdir -p "$OUT_DIR"

if [ ! -f "$CODE_FILE" ]; then
  echo "No Level 2 solver is currently present in $ROOT_DIR/code/."
  echo "Add your Basilisk C file as level2_thermal.c before running this script."
  exit 1
fi

if ! command -v qcc >/dev/null 2>&1; then
  echo "qcc was not found on your PATH. Install Basilisk and make sure qcc is visible."
  exit 1
fi

qcc -O2 -Wall -disable-dimensions "$CODE_FILE" -o "$OUT_DIR/level2_thermal" -lm
exec "$OUT_DIR/level2_thermal" "${@:-9 50.0 4.0 1.0 default}"
