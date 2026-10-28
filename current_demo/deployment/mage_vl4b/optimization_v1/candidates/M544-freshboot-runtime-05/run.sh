#!/bin/bash
set -euo pipefail
[[ $EUID == 0 && $# == 2 ]] || exit 65
here=/dev/shm/m523_PS3072_ttft_package01
[[ $(sha256sum "$0" | cut -d" " -f1) == "$1" ]] || exit 66
export XILINX_XRT=/usr TMPDIR=/dev/shm PATH=/usr/local/share/pynq-venv/bin:$PATH
exec /usr/local/share/pynq-venv/bin/python -I -B "$here/native.py" eab348ba6da326736b8ca3a21028f05b488cc5f8f49fdc106fdd25829177ef59 Request --component-manifest-sha "$2" --enable-saved-fixture-gate
