#!/usr/bin/env bash
set -euo pipefail
[[ $EUID == 0 ]] || exit 65
cd "$(dirname "${BASH_SOURCE[0]}")"
task_manifest=${1:?manifest}
task_mode=${2:?Run or Collect}
task_python=/usr/local/share/pynq-venv/bin/python
export PYTHONDONTWRITEBYTECODE=1
export XILINX_XRT=/usr TMPDIR=/dev/shm
export PATH=/usr/local/share/pynq-venv/bin:$PATH
printf '%s  PACKAGE_MANIFEST.json
' "$task_manifest" | sha256sum -c -
sha256sum -c SHA256SUMS
if [[ $task_mode == Collect ]]; then exec "$task_python" -B ./m430_export.py; fi
[[ $task_mode == Run && ${M430_ENABLE_VISUAL_PERFORMANCE:-0} == 1 ]] || exit 66
[[ ! -e /home/ubuntu/m430_late11_visual_warm_01 ]] || exit 67
set +e
"$task_python" -B ./m430_gate.py "$task_manifest" --enable-visual-performance
task_gate_rc=$?
"$task_python" -B ./m430_export.py
task_export_rc=$?
set -e
echo "M430_DONE gate_rc=$task_gate_rc export_rc=$task_export_rc"
if [[ $task_gate_rc != 0 ]]; then exit "$task_gate_rc"; fi
exit "$task_export_rc"
