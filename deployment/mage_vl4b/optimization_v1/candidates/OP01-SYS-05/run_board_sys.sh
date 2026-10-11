#!/usr/bin/env bash
set -euo pipefail
here=$(cd -- "$(dirname -- "$0")" && pwd)
export PYTHONDONTWRITEBYTECODE=1 XILINX_XRT=/usr TMPDIR=/dev/shm
export PATH=/usr/local/share/pynq-venv/bin:$PATH
export OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=4
exec /usr/local/share/pynq-venv/bin/python -B "$here/op01_board_sys.py" "$@"
