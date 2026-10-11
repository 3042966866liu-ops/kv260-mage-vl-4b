#!/usr/bin/env bash
set -euo pipefail
[[ $EUID == 0 ]] || exit 65
cd "$(dirname "${BASH_SOURCE[0]}")"
task_manifest=${1:?manifest}
task_mode=${2:?Run or Collect}
task_gate=${3:?Descriptor or Chain}
[[ $task_gate == Descriptor || $task_gate == Chain ]] || exit 66
task_python=/usr/local/share/pynq-venv/bin/python
export PYTHONDONTWRITEBYTECODE=1
if [[ $task_mode == Collect ]]; then exec "$task_python" -B ./m418_export.py "$task_gate"; fi
[[ $task_mode == Run && ${M418_ENABLE_VISUAL:-0} == 1 ]] || exit 66
export XILINX_XRT=/usr TMPDIR=/dev/shm
export PATH=/usr/local/share/pynq-venv/bin:$PATH
printf '%s  PACKAGE_MANIFEST.json\n' "$task_manifest" | sha256sum -c -
sha256sum -c SHA256SUMS
[[ ! -e /home/ubuntu/m418_visual_linear_01/$task_gate ]] || exit 67
task_args=("$task_manifest" "$task_gate" --enable-visual-linear-gate)
if [[ $task_gate == Chain ]]; then task_args+=(--prior-sha "${4:?prior raw}"); fi
set +e
"$task_python" -B ./m418_probe.py "${task_args[@]}"
task_gate_rc=$?
"$task_python" -B ./m418_export.py "$task_gate"
task_export_rc=$?
set -e
echo "M418_DONE gate_rc=$task_gate_rc export_rc=$task_export_rc"
if [[ $task_gate_rc != 0 ]]; then exit "$task_gate_rc"; fi
exit "$task_export_rc"
