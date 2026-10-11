#!/usr/bin/env bash
set -euo pipefail
[[ $EUID == 0 ]] || exit 65
task_dir=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)
task_python=/usr/local/share/pynq-venv/bin/python
[[ $# == 2 ]] || exit 64
if [[ $2 == Collect ]]; then "$task_python" -B "$task_dir/m358_export_result.py"; exit 0; fi
[[ $2 == Run && ${M358_ENABLE_LOAD_ONLY:-0} == 1 ]] || exit 66
[[ ! -e /home/ubuntu/m358_candidate_capacity_01 ]] || exit 67
export XILINX_XRT=/usr TMPDIR=/dev/shm PATH=/usr/local/share/pynq-venv/bin:$PATH
set +e
"$task_python" -B "$task_dir/m358_load_only_probe.py" "$1" --enable-load-only
task_gate_rc=$?
"$task_python" -B "$task_dir/m358_export_result.py"
task_export_rc=$?
set -e
echo "M358_DONE gate_rc=$task_gate_rc export_rc=$task_export_rc"
if [[ $task_gate_rc != 0 ]]; then exit "$task_gate_rc"; fi
exit "$task_export_rc"
