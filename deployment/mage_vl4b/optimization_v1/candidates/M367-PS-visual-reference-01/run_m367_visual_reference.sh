#!/usr/bin/env bash
set -euo pipefail
[[ $EUID == 0 && $# == 3 && $3 == PS1 ]] || exit 64
task_dir=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)
task_python=/usr/local/share/pynq-venv/bin/python
if [[ $2 == Collect ]]; then "$task_python" -B "$task_dir/m367_export_result.py"; exit 0; fi
[[ $2 == Run && ${M367_ENABLE_PS_REFERENCE:-0} == 1 ]] || exit 66
[[ ! -e /home/ubuntu/m367_visual_reference_01 ]] || exit 67
set +e
"$task_python" -B "$task_dir/m367_visual_reference_gate.py" "$1" --enable-ps-reference
task_gate_rc=$?
"$task_python" -B "$task_dir/m367_export_result.py"
task_export_rc=$?
set -e
echo "M367_DONE case=PS1 gate_rc=$task_gate_rc export_rc=$task_export_rc"
if [[ $task_gate_rc != 0 ]]; then exit "$task_gate_rc"; fi
exit "$task_export_rc"
