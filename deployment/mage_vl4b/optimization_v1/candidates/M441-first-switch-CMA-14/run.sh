#!/usr/bin/env bash
set -euo pipefail
[[ $EUID == 0 && $# == 2 ]] || exit 65
cd "$(dirname "${BASH_SOURCE[0]}")"
if [[ $2 == Collect ]]; then /usr/local/share/pynq-venv/bin/python -B ./m441_switch_export13.py; exit 0; fi
[[ $2 == Run ]] || exit 66
printf "%s  PACKAGE_MANIFEST.json\n" "$1" | sha256sum -c -
sha256sum -c SHA256SUMS
[[ ! -e /home/ubuntu/m441_first_switch_cma_evidence_14 ]] || exit 67
export XILINX_XRT=/usr TMPDIR=/dev/shm PATH=/usr/local/share/pynq-venv/bin:$PATH
set +e
/usr/local/share/pynq-venv/bin/python -I -B ./m441_switch_entry13.py --enable-first-switch-only
original_gate_rc=$?
/usr/local/share/pynq-venv/bin/python -B ./m441_switch_export13.py
export_rc=$?
set -e
printf "M441D_DONE original_gate_rc=%s export_rc=%s\n" "$original_gate_rc" "$export_rc"
if [[ $original_gate_rc != 0 ]]; then exit "$original_gate_rc"; fi
exit "$export_rc"
