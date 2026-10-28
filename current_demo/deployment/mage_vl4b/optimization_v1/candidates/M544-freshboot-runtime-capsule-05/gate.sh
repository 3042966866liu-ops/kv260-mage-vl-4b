#!/bin/bash
set -euo pipefail
[[ $EUID == 0 && $# == 4 ]] || exit 65
[[ $(sha256sum "$0" | cut -d" " -f1) == "$1" ]] || exit 66
export XILINX_XRT=/usr TMPDIR=/dev/shm PATH=/usr/local/share/pynq-venv/bin:$PATH
exec /usr/local/share/pynq-venv/bin/python -I -B /dev/shm/m523_PS3072_ttft_package01/minimal_gate.py 366bca419461ba41867b4f7008dedf908e825d38f08a4757f9decd258c3cac09 "$3" --component-manifest-sha "$2" --enable-saved-fixture-gate --prior-sha "$4"
