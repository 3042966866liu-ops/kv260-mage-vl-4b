#!/bin/bash
set -euo pipefail
[[ $EUID == 0 && ( $# == 3 || $# == 5 ) ]] || exit 65
here=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)
[[ $(sha256sum "$0" | cut -d" " -f1) == "$1" ]] || exit 66
shift
export XILINX_XRT=/usr TMPDIR=/dev/shm PATH=/usr/local/share/pynq-venv/bin:$PATH
exec /usr/local/share/pynq-venv/bin/python -I -B "$here/M455_P1_shape52301.py" "$@" --enable-saved-fixture-gate
