#!/usr/bin/env bash
set -euo pipefail

root=/home/ubuntu/tellme_m120_m89x2_20260901
candidate=$root/m254_dual_path_web_candidate
m243=$root/m243_web_prefill_delta
m242=$root/m242_m241_fixed_text_delta
patch=$root/m227_runtime_base_patch
gate=$root/m223_realtime_delta
old_gate=$root/m218_dual_source_delta
video=$root/m181_m120_video_board_candidate
text=$root/m175_m120_fixed_text_candidate
weights=$root/m120_fulltext_weights_0x4D395832
pid_file=$root/results/m223_realtime_service.pid
manifest_sha256=${1:?M254 manifest SHA-256 required}
attempt=${2:?M254 attempt identifier required}
[[ $attempt =~ ^[0-9][0-9]$ ]] || { echo M254_ATTEMPT_FORMAT_INVALID >&2; exit 2; }
formal=$root/results/M254_DUAL_PATH_WEB_BOARD_RESULT_$attempt.json
service_stopped=0
new_pid=0

start_stable(){
  env PYTHONPATH=$m243:$m242:$patch:$gate:$old_gate:$video:$root/m190_mage_runtime:$text/runtime \
    M200_STATIC_ROOT=$gate/static nohup /usr/local/share/pynq-venv/bin/python "$m243/m243_video_server.py" \
    --candidate "$video" --text-candidate "$text" --weights-root "$weights" \
    --board-gate "$gate/M223_PREDECESSOR_SUMMARY.json" --host 0.0.0.0 --port 8001 \
    > "$root/results/m254_rollback_m243_service.log" 2>&1 &
  rollback_pid=$!; echo "$rollback_pid" > "$pid_file"
}
finish(){ rc=$?; trap - EXIT; if [[ $rc -ne 0 && $service_stopped -eq 1 ]]; then if [[ $new_pid -gt 0 ]]; then kill "$new_pid" 2>/dev/null || true; fi; start_stable; fi; echo "__M254_RUNNER_RC_${rc}__"; exit "$rc"; }
trap finish EXIT

[[ $(id -u) -eq 0 ]] || { echo M254_ROOT_REQUIRED >&2; exit 1; }
[[ ! -e $formal ]] || { echo M254_FORMAL_RESULT_ALREADY_EXISTS >&2; exit 1; }
[[ -e $pid_file ]] || { echo M254_STABLE_PID_MISSING >&2; exit 1; }
export XILINX_XRT=/usr TMPDIR=/dev/shm PYTHONDONTWRITEBYTECODE=1 TRANSFORMERS_OFFLINE=1 HF_HUB_OFFLINE=1
export PATH=/usr/local/share/pynq-venv/bin:/usr/local/bin:/usr/bin:/bin
export PYTHONPATH=$candidate:$m243:$m242:$patch:$gate:$old_gate:$video:$root/m190_mage_runtime:$text/runtime
export M200_STATIC_ROOT=$candidate/static
export M254_M243_RESULT=$candidate/M243_WEB_PREFILL_BOARD_RESULT_05.json
export M254_M253_RESULT=$candidate/M253_KV260_LATEST_FAST_STREAM_BOARD_RESULT_02.json
export M254_M249_RESULT=$candidate/M249_KV260_SSDLITE_BOARD_RESULT_03.json
export M254_M249_CANDIDATE=$root/m249_ssdlite_board_candidate

python3 "$candidate/verify_m254_candidate.py" --root "$candidate" --expected-manifest-sha256 "$manifest_sha256"
python3 "$text/runtime/m120_board_env_preflight.py" --candidate "$text" --expected-package-manifest-sha256 406dcca340e4604baeb761445795391c43ec26bd99fa06ffae893d597b17414f --result "$root/results/m254_environment_$attempt.json"

old_pid=$(tr -dc '0-9' < "$pid_file")
[[ -n $old_pid && -r /proc/$old_pid/cmdline ]] || { echo M254_STABLE_PROCESS_MISSING >&2; exit 1; }
old_command=$(tr '\0' ' ' < "/proc/$old_pid/cmdline")
[[ $old_command == *m243_video_server.py* && $old_command == *"--port 8001"* ]] || { echo "M254_REFUSE_UNKNOWN_PROCESS=$old_command" >&2; exit 1; }
kill "$old_pid"
for _ in $(seq 1 40); do if ! kill -0 "$old_pid" 2>/dev/null; then break; fi; sleep 0.25; done
if kill -0 "$old_pid" 2>/dev/null; then echo M254_STABLE_STOP_TIMEOUT >&2; exit 1; fi
service_stopped=1

nohup /usr/local/share/pynq-venv/bin/python "$candidate/m254_video_server.py" \
  --candidate "$video" --text-candidate "$text" --weights-root "$weights" \
  --board-gate "$gate/M223_PREDECESSOR_SUMMARY.json" --host 0.0.0.0 --port 8001 \
  > "$root/results/m254_dual_path_web_service.log" 2>&1 &
new_pid=$!; echo "$new_pid" > "$pid_file"
python3 "$candidate/m254_runtime_ready_probe.py" --manifest-sha256 "$manifest_sha256" --pid "$new_pid" --result "$formal" --timeout-seconds 240
service_stopped=0
echo M254_DUAL_PATH_WEB_BOARD_RUNNER_PASS

