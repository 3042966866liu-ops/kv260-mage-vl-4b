#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PYTHON=/usr/local/share/pynq-venv/bin/python3
if [[ ! -x "$PYTHON" ]]; then
  echo "BLOCKED: expected PYNQ Python is unavailable: $PYTHON" >&2
  exit 2
fi
export XILINX_XRT=/usr
export TMPDIR=/dev/shm
export PATH="/usr/local/share/pynq-venv/bin:$PATH"
exec "$PYTHON" "$ROOT/scripts/preflight.py" --config "$ROOT/configs/deployment.example.json" --run "$@"
