#!/usr/bin/env bash
set -euo pipefail

root=/home/ubuntu/tellme_m120_m89x2_20260901
gate=$root/m218_dual_source_delta
old_gate=$root/m212_live_delta
video=$root/m181_m120_video_board_candidate
text=$root/m175_m120_fixed_text_candidate
weights=$root/m120_fulltext_weights_0x4D395832
result_dir=$root/results/m218_dual_source_service_01
formal=$root/results/M218_DUAL_SOURCE_SERVICE_BOARD_RESULT_01.json
old_pid_file=$root/results/m212_live_service.pid
new_pid_file=$root/results/m218_dual_source_service.pid
text_manifest=406dcca340e4604baeb761445795391c43ec26bd99fa06ffae893d597b17414f
package_manifest_sha256=${1:?M218 package manifest SHA-256 required}
old_stopped=0
new_pid=0

rollback_old_service() {
  if [[ $new_pid -gt 0 ]] && kill -0 "$new_pid" 2>/dev/null; then
    kill "$new_pid" 2>/dev/null || true
  fi
  if [[ $old_stopped -eq 1 ]]; then
    M200_STATIC_ROOT=$old_gate/static nohup /usr/local/share/pynq-venv/bin/python \
      "$old_gate/video_server.py" --candidate "$video" --text-candidate "$text" \
      --weights-root "$weights" --board-gate "$old_gate/M212_PREDECESSOR_SUMMARY.json" \
      --host 0.0.0.0 --port 8001 > "$root/results/m212_live_service.log" 2>&1 &
    rollback_pid=$!
    echo "$rollback_pid" > "$old_pid_file"
    echo "M218_ROLLBACK_M212_SERVICE_PID=$rollback_pid" >&2
  fi
}

finish() {
  rc=$?
  trap - EXIT
  if [[ $rc -ne 0 ]]; then rollback_old_service; fi
  echo "__M218_LIVE_RUNNER_RC_${rc}__"
  exit "$rc"
}
trap finish EXIT

[[ $(id -u) -eq 0 ]] || { echo M218_ROOT_REQUIRED >&2; exit 1; }
[[ ! -e $formal ]] || { echo M218_FORMAL_RESULT_ALREADY_EXISTS >&2; exit 1; }
[[ -e $old_pid_file ]] || { echo M218_OLD_SERVICE_PID_MISSING >&2; exit 1; }
mkdir -p "$result_dir"
export XILINX_XRT=/usr TMPDIR=/dev/shm PYTHONDONTWRITEBYTECODE=1 TRANSFORMERS_OFFLINE=1 HF_HUB_OFFLINE=1
export PATH=/usr/local/share/pynq-venv/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin
export PYTHONPATH=$gate:$video:$root/m190_mage_runtime

/usr/local/share/pynq-venv/bin/python "$gate/m218_verify_board_delta.py" \
  --root "$gate" --expected-manifest-sha256 "$package_manifest_sha256"
/usr/local/share/pynq-venv/bin/python "$text/runtime/m120_board_env_preflight.py" \
  --candidate "$text" --expected-package-manifest-sha256 "$text_manifest" \
  --result "$result_dir/environment.json"
/usr/local/share/pynq-venv/bin/python "$gate/video_server.py" \
  --candidate "$video" --text-candidate "$text" --weights-root "$weights" \
  --board-gate "$gate/M218_PREDECESSOR_SUMMARY.json" --preflight \
  --result "$result_dir/service_preflight.json"

old_pid=$(tr -dc '0-9' < "$old_pid_file")
[[ -n $old_pid ]] || { echo M218_OLD_SERVICE_PID_INVALID >&2; exit 1; }
[[ -r /proc/$old_pid/cmdline ]] || { echo M218_OLD_SERVICE_PROCESS_MISSING >&2; exit 1; }
old_command=$(tr '\0' ' ' < "/proc/$old_pid/cmdline")
[[ $old_command == *m212_live_delta/video_server.py* && $old_command == *"--port 8001"* ]] || {
  echo "M218_REFUSE_UNKNOWN_OLD_PROCESS=$old_command" >&2
  exit 1
}
kill "$old_pid"
for _ in $(seq 1 20); do
  if ! kill -0 "$old_pid" 2>/dev/null; then break; fi
  sleep 0.25
done
if kill -0 "$old_pid" 2>/dev/null; then echo M218_OLD_SERVICE_STOP_TIMEOUT >&2; exit 1; fi
mv "$old_pid_file" "$old_pid_file.replaced-by-m218"
old_stopped=1

if ! ip -4 addr show dev eth0 | grep -q '192.168.0.2/24'; then
  ip addr add 192.168.0.2/24 dev eth0
  echo added > "$result_dir/temporary_ip_state"
else
  echo existing > "$result_dir/temporary_ip_state"
fi
M200_STATIC_ROOT=$gate/static nohup /usr/local/share/pynq-venv/bin/python \
  "$gate/video_server.py" --candidate "$video" --text-candidate "$text" \
  --weights-root "$weights" --board-gate "$gate/M218_PREDECESSOR_SUMMARY.json" \
  --host 0.0.0.0 --port 8001 > "$root/results/m218_dual_source_service.log" 2>&1 &
new_pid=$!
echo "$new_pid" > "$new_pid_file"
/usr/local/share/pynq-venv/bin/python "$gate/m218_health_probe.py" \
  --url http://127.0.0.1:8001/api/health \
  --preflight "$result_dir/service_preflight.json" \
  --package-manifest-sha256 "$package_manifest_sha256" \
  --pid "$new_pid" --result "$formal"
old_stopped=0
echo M218_DUAL_SOURCE_SERVICE_BOARD_START_PASS
