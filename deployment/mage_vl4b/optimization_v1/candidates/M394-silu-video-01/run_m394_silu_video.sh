#!/usr/bin/env bash
set -euo pipefail
[[ $EUID == 0 ]] || exit 65
task_dir=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)
task_python=/usr/local/share/pynq-venv/bin/python
export PYTHONDONTWRITEBYTECODE=1
[[ $# == 3 && $3 == B1 ]] || exit 64
if [[ $2 == Collect ]]; then "$task_python" -B "$task_dir/m394_export_result.py" "$3"; exit 0; fi
[[ $2 == Run && ${M394_ENABLE_SILU_VIDEO:-0} == 1 ]] || exit 66
[[ ! -e /home/ubuntu/m394_silu_video_01/$3 ]] || exit 67
export XILINX_XRT=/usr TMPDIR=/dev/shm PATH=/usr/local/share/pynq-venv/bin:$PATH
set +e
"$task_python" -B "$task_dir/m394_silu_video_gate.py" "$1" "$3" --enable-silu-video
task_gate_rc=$?
"$task_python" -B "$task_dir/m394_export_result.py" "$3"
task_export_rc=$?
set -e
echo "M394_DONE case=$3 gate_rc=$task_gate_rc export_rc=$task_export_rc"
if [[ $task_gate_rc != 0 ]]; then exit "$task_gate_rc"; fi
exit "$task_export_rc"
