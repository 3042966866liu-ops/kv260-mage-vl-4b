#!/usr/bin/env bash
set -euo pipefail
[[ $EUID == 0 && $# == 2 ]] || exit 65
task_dir=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)
task_python=/usr/local/share/pynq-venv/bin/python
if [[ $2 == Collect ]]; then "$task_python" -B "$task_dir/m423_export.py"; exit 0; fi
[[ $2 == Run && ${M423_ENABLE_SAVED_FEATURES:-0} == 1 ]] || exit 66
[[ ! -e /home/ubuntu/m423_integrated_video_01 ]] || exit 67
export XILINX_XRT=/usr TMPDIR=/dev/shm PATH=/usr/local/share/pynq-venv/bin:$PATH
set +e
"$task_python" -B "$task_dir/m423_gate.py" "$1" B1 --enable-staged-video
task_gate_rc=$?
"$task_python" -B "$task_dir/m423_export.py"
task_export_rc=$?
set -e
echo "M423_DONE gate_rc=$task_gate_rc export_rc=$task_export_rc"
if [[ $task_gate_rc != 0 ]]; then exit "$task_gate_rc"; fi
exit "$task_export_rc"
