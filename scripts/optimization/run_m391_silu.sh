#!/usr/bin/env bash
set -euo pipefail
[[ $EUID == 0 && $# == 2 ]] || exit 64
task_dir=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)
task_python=/usr/local/share/pynq-venv/bin/python
export PYTHONDONTWRITEBYTECODE=1
if [[ $2 == Collect ]]; then "$task_python" -B "$task_dir/m391_export.py"; exit 0; fi
[[ $2 == Run && ${M391_ENABLE_COMPONENT:-0} == 1 ]] || exit 66
[[ ! -e /home/ubuntu/m391_silu_component_01 ]] || exit 67
set +e
"$task_python" -B "$task_dir/m391_silu_gate.py" "$1" --enable-component
task_gate_rc=$?
"$task_python" -B "$task_dir/m391_export.py"
task_export_rc=$?
set -e
echo "M391_DONE gate_rc=$task_gate_rc export_rc=$task_export_rc"
if [[ $task_gate_rc != 0 ]]; then exit "$task_gate_rc"; fi
exit "$task_export_rc"
