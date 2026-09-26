#!/usr/bin/env bash
set -euo pipefail

root=/home/ubuntu/tellme_m120_m89x2_20260901
delta=$root/m246_knife_binary_delta
m243=$root/m243_web_prefill_delta
m242=$root/m242_m241_fixed_text_delta
patch=$root/m227_runtime_base_patch
gate=$root/m223_realtime_delta
old_gate=$root/m218_dual_source_delta
video=$root/m181_m120_video_board_candidate
text=$root/m175_m120_fixed_text_candidate
weights=$root/m120_fulltext_weights_0x4D395832
pid_file=$root/results/m223_realtime_service.pid
python=/usr/local/share/pynq-venv/bin/python
manifest_sha256=${1:?M246 manifest SHA-256 required}
m243_result_sha256=${2:?M243 result SHA-256 required}
attempt=${3:?M246 attempt identifier required}
[[ $attempt =~ ^[0-9][0-9]$ ]] || { echo M246_ATTEMPT_FORMAT_INVALID >&2; exit 2; }
result_dir=$root/results/m246_knife_runtime_$attempt
formal=$root/results/M246_KNIFE_RUNTIME_BOARD_RESULT_$attempt.json
m243_result=$root/results/M243_WEB_PREFILL_BOARD_RESULT_05.json
service_stopped=0
new_pid=0

start_previous(){
  env PYTHONPATH=$m243:$m242:$patch:$gate:$old_gate:$video:$root/m190_mage_runtime:$text/runtime \
    M200_STATIC_ROOT=$gate/static \
    nohup "$python" "$m243/m243_video_server.py" \
    --candidate "$video" --text-candidate "$text" --weights-root "$weights" \
    --board-gate "$gate/M223_PREDECESSOR_SUMMARY.json" --host 0.0.0.0 --port 8001 \
    > "$root/results/m246_rollback_m243_service.log" 2>&1 &
  rollback_pid=$!; echo "$rollback_pid" > "$pid_file"
}
finish(){
  rc=$?; trap - EXIT
  if [[ $rc -ne 0 && $service_stopped -eq 1 ]]; then
    if [[ $new_pid -gt 0 ]]; then kill "$new_pid" 2>/dev/null || true; fi
    start_previous
  fi
  echo "__M246_RUNNER_RC_${rc}__"
  exit "$rc"
}
trap finish EXIT

[[ $(id -u) -eq 0 ]] || { echo M246_ROOT_REQUIRED >&2; exit 1; }
[[ ! -e $formal ]] || { echo M246_FORMAL_RESULT_ALREADY_EXISTS >&2; exit 1; }
[[ -e $pid_file ]] || { echo M246_PREVIOUS_PID_MISSING >&2; exit 1; }
mkdir -p "$result_dir"
export XILINX_XRT=/usr TMPDIR=/dev/shm PYTHONDONTWRITEBYTECODE=1 TRANSFORMERS_OFFLINE=1 HF_HUB_OFFLINE=1
export PATH=/usr/local/share/pynq-venv/bin:/usr/local/bin:/usr/bin:/bin
export PYTHONPATH=$delta:$m243:$m242:$patch:$gate:$old_gate:$video:$root/m190_mage_runtime:$text/runtime

"$python" "$delta/m246_verify_package.py" \
  --root "$delta" --expected-manifest-sha256 "$manifest_sha256" \
  --m243-result "$m243_result" --expected-m243-result-sha256 "$m243_result_sha256"
"$python" "$text/runtime/m120_board_env_preflight.py" \
  --candidate "$text" \
  --expected-package-manifest-sha256 406dcca340e4604baeb761445795391c43ec26bd99fa06ffae893d597b17414f \
  --result "$result_dir/environment.json"
"$python" "$delta/m246_video_server.py" \
  --candidate "$video" --text-candidate "$text" --weights-root "$weights" \
  --board-gate "$gate/M223_PREDECESSOR_SUMMARY.json" --preflight \
  --result "$result_dir/service_preflight.json"

old_pid=$(tr -dc '0-9' < "$pid_file")
[[ -n $old_pid && -r /proc/$old_pid/cmdline ]] || { echo M246_M243_PROCESS_MISSING >&2; exit 1; }
old_command=$(tr '\0' ' ' < "/proc/$old_pid/cmdline")
[[ $old_command == *m243_web_prefill_delta/m243_video_server.py* && $old_command == *"--port 8001"* ]] || {
  echo "M246_REFUSE_UNKNOWN_PROCESS=$old_command" >&2; exit 1;
}
kill "$old_pid"
for _ in $(seq 1 20); do if ! kill -0 "$old_pid" 2>/dev/null; then break; fi; sleep 0.25; done
if kill -0 "$old_pid" 2>/dev/null; then echo M246_M243_STOP_TIMEOUT >&2; exit 1; fi
service_stopped=1

M200_STATIC_ROOT=$gate/static nohup "$python" "$delta/m246_video_server.py" \
  --candidate "$video" --text-candidate "$text" --weights-root "$weights" \
  --board-gate "$gate/M223_PREDECESSOR_SUMMARY.json" --host 0.0.0.0 --port 8001 \
  > "$root/results/m246_knife_runtime_service.log" 2>&1 &
new_pid=$!; echo "$new_pid" > "$pid_file"
"$python" "$delta/m246_runtime_ready_probe.py" \
  --manifest-sha256 "$manifest_sha256" --pid "$new_pid" --result "$formal" \
  --timeout-seconds 180
service_stopped=0
echo M246_KNIFE_RUNTIME_BOARD_RUNNER_PASS
