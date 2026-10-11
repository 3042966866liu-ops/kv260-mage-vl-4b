#!/usr/bin/env bash
set -euo pipefail
[[ $# -eq 2 ]] || exit 2
export XILINX_XRT=/usr TMPDIR=/dev/shm PYTHONDONTWRITEBYTECODE=1
export PATH=/usr/local/share/pynq-venv/bin:/usr/local/bin:/usr/bin:/bin
here=$(cd -- "$(dirname -- "$0")" && pwd)
exec /usr/local/share/pynq-venv/bin/python -B "$here/op00_board_audit.py" --manifest-sha256 "$1" --result "$2"
