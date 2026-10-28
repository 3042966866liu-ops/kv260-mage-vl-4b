#!/bin/bash
set -euo pipefail
test "$#" -eq 3
[[ "$3" =~ ^[0-9a-f]{32}$ ]]
export CAMPUS_SESSION_ID="$3"
printf '%s  %s\n' "$1" "$0" | sha256sum --check --status
test "$(id -u)" -eq 0
export XILINX_XRT=/usr
export TMPDIR=/dev/shm
export PATH=/usr/local/share/pynq-venv/bin:$PATH
set +e
/usr/local/share/pynq-venv/bin/python -I -B "$(dirname "$0")/launcher.py" "$2"
gate_rc=$?
set -e
exit "$gate_rc"
