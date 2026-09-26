#!/usr/bin/env bash
set -euo pipefail
here=$(cd -- "$(dirname -- "$0")" && pwd)
export PYTHONDONTWRITEBYTECODE=1 XILINX_XRT=/usr TMPDIR=/dev/shm
export PATH=/usr/local/share/pynq-venv/bin:/usr/local/bin:/usr/bin:/bin
export OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=4
exec /usr/local/share/pynq-venv/bin/python -B "$here/board_decode_one_layer.py" --full-decode "$@"
