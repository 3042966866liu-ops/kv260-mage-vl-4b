#!/bin/bash
set -euo pipefail
if [[ $# -lt 3 || $# -gt 4 ]]; then exit 64; fi
task_mode=$1
task_manifest=$2
task_action=$3
task_here=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)
case "$task_mode" in BuildID|Descriptor|Chain|Compare) ;; *) exit 64;; esac
if [[ $EUID -ne 0 ]]; then exit 65; fi
task_python=/usr/local/share/pynq-venv/bin/python
if [[ $task_action == Collect ]]; then
  "$task_python" -B "$task_here/m441_export_result.py" "$task_mode"
  exit 0
fi
if [[ $task_action != Run || ${M441_ENABLE_GATE:-0} != 1 ]]; then exit 66; fi
task_result=/home/ubuntu/m441_board_evidence_01/$task_mode
if [[ -e $task_result ]]; then echo 'Existing attempt; collect only'; exit 67; fi
export XILINX_XRT=/usr
export TMPDIR=/dev/shm
export PATH=/usr/local/share/pynq-venv/bin:$PATH
task_args=("$task_manifest" "$task_mode" --enable-candidate-gate)
if [[ $# == 4 ]]; then task_args+=(--prior-sha "$4"); fi
set +e
"$task_python" -B "$task_here/m441_board_probe.py" "${task_args[@]}"
task_gate_rc=$?
"$task_python" -B "$task_here/m441_export_result.py" "$task_mode"
task_export_rc=$?
set -e
echo "M441_DONE gate_rc=$task_gate_rc export_rc=$task_export_rc"
if [[ $task_gate_rc != 0 ]]; then exit "$task_gate_rc"; fi
exit "$task_export_rc"
