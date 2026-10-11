#!/usr/bin/env bash
set -euo pipefail
[[ $EUID == 0 ]] || exit 65
cd "$(dirname "${BASH_SOURCE[0]}")"
task_manifest=${1:?manifest}
task_mode=${2:?Run or Collect}
task_python=/usr/local/share/pynq-venv/bin/python
export PYTHONDONTWRITEBYTECODE=1
if [[ $task_mode == Collect ]]; then exec "$task_python" -B ./m426_export.py; fi
[[ $task_mode == Run && ${M426_ENABLE_SOFTWARE_RANGE:-0} == 1 ]] || exit 66
printf '%s  PACKAGE_MANIFEST.json\n' "$task_manifest" | sha256sum -c -
sha256sum -c SHA256SUMS
[[ ! -e /home/ubuntu/m426_range_software_01 ]] || exit 67
set +e
"$task_python" -B ./m426_gate.py "$task_manifest" --enable-software-range
task_gate_rc=$?
"$task_python" -B ./m426_export.py
task_export_rc=$?
set -e
echo "M426_DONE gate_rc=$task_gate_rc export_rc=$task_export_rc"
if [[ $task_gate_rc != 0 ]]; then exit "$task_gate_rc"; fi
exit "$task_export_rc"
