#!/usr/bin/env bash
set -euo pipefail

root=/home/ubuntu/tellme_m120_m89x2_20260901
patch=$root/m227_runtime_base_patch
pid_file=$root/results/m223_realtime_service.pid
result=$root/results/m235_parse_launch_overlap_01/service_post_failure_verified.json

export XILINX_XRT=/usr TMPDIR=/dev/shm PYTHONDONTWRITEBYTECODE=1
export PATH=/usr/local/share/pynq-venv/bin:/usr/local/bin:/usr/bin:/bin

[[ $(id -u) -eq 0 ]] || { echo M235_POST_FAIL_ROOT_REQUIRED >&2; exit 1; }
[[ -s $pid_file ]] || { echo M235_POST_FAIL_PID_MISSING >&2; exit 1; }
pid=$(tr -dc '0-9' < "$pid_file")
[[ -n $pid && -r /proc/$pid/cmdline ]] || { echo M235_POST_FAIL_PROCESS_MISSING >&2; exit 1; }
command=$(tr '\0' ' ' < "/proc/$pid/cmdline")
[[ $command == *m223_realtime_delta/m222_video_server.py* && $command == *"--port 8001"* ]] || {
  echo "M235_POST_FAIL_REFUSE_UNKNOWN_SERVICE=$command" >&2
  exit 1
}
rm -f "$result"
python3 "$patch/m227_health_probe.py" --url http://127.0.0.1:8001/api/health \
  --patch-manifest-sha256 0bab466470fe09ef1b548921235a365ac3832c6264bf2e3a16ee19a6a3aad13c \
  --pid "$pid" --result "$result"
echo M235_POST_FAILURE_SERVICE_PASS
