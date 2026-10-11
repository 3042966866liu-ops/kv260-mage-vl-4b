#!/usr/bin/env bash
set -euo pipefail
export XILINX_XRT=/usr
export TMPDIR=/dev/shm
export PATH=/usr/local/share/pynq-venv/bin:/usr/local/bin:/usr/bin:/bin
export PYTHONDONTWRITEBYTECODE=1
runner_dir=$(cd -- "$(dirname -- "$0")" && pwd)
exec /usr/local/share/pynq-venv/bin/python -B "$runner_dir/decode_one_minimal_board.py" --manifest-sha256 "$1" --result "$2" --real-chain
