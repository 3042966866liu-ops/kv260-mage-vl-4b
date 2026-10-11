#!/usr/bin/env bash
set -euo pipefail
[[ $EUID == 0 ]] || exit 65
cd "$(dirname "${BASH_SOURCE[0]}")"
task_manifest=${1:?manifest}
task_mode=${2:?Run or Collect}
task_python=/usr/local/share/pynq-venv/bin/python
export PYTHONDONTWRITEBYTECODE=1
if [[ $task_mode == Collect ]]; then exec "$task_python" -B ./m409_gate.py Collect; fi
[[ $task_mode == Run && ${M409_ENABLE_REFERENCE:-0} == 1 ]] || exit 66
printf '%s  PACKAGE_MANIFEST.json\n' "$task_manifest" | sha256sum -c -
sha256sum -c SHA256SUMS
[[ ! -e /home/ubuntu/m409_mlp_reference_01 ]] || exit 67
set +e
"$task_python" -B ./m409_gate.py "$task_manifest" --enable-saved-MLP-reference
task_gate_rc=$?
"$task_python" -B ./m409_gate.py Collect
task_export_rc=$?
set -e
echo "M409_DONE gate_rc=$task_gate_rc export_rc=$task_export_rc"
if [[ $task_gate_rc != 0 ]]; then exit "$task_gate_rc"; fi
exit "$task_export_rc"
