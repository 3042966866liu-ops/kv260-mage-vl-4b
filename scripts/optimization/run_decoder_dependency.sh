#!/usr/bin/env bash
set -euo pipefail
export PYTHONDONTWRITEBYTECODE=1
export XILINX_XRT=/usr
export TMPDIR=/dev/shm
export PATH=/usr/local/share/pynq-venv/bin:$PATH
here=$(cd -- "$(dirname -- "$0")" && pwd)
exec /usr/bin/python3 "$here/install_decoder_dependency.py" "$@"
