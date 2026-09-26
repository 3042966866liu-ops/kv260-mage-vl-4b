#!/usr/bin/env bash
set -euo pipefail

root=/home/ubuntu/tellme_m120_m89x2_20260901
candidate=$root/m277_m276_fixed_window_candidate
m254=$root/m254_dual_path_web_candidate
m243=$root/m243_web_prefill_delta
m242=$root/m242_m241_fixed_text_delta
patch=$root/m227_runtime_base_patch
gate=$root/m223_realtime_delta
old_gate=$root/m218_dual_source_delta
video=$root/m181_m120_video_board_candidate
text=$root/m175_m120_fixed_text_candidate
weights=$root/m120_fulltext_weights_0x4D395832
m249=$root/m249_ssdlite_board_candidate
fixtures=$m249/fixtures
torchvision_site=/dev/shm/tellme_m254_torchvision
pid_file=$root/results/m223_realtime_service.pid
python=/usr/local/share/pynq-venv/bin/python
manifest_sha256=${1:?M277 manifest SHA-256 required}
m270_sha256=${2:?M270 result SHA-256 required}
m254_manifest_sha256=${3:?active M254 manifest SHA-256 required}
attempt=${4:?M277 attempt identifier required}
[[ $attempt =~ ^[0-9][0-9]$ ]] || { echo M277_ATTEMPT_FORMAT_INVALID >&2; exit 2; }
result_dir=$root/results/m277_m276_fixed_window_$attempt
formal=$result_dir/result.json
restore_result=$result_dir/restore_m254.json
service_stopped=0
restore_attempted=0
new_pid=0

start_active_m254(){
  export PYTHONPATH=$torchvision_site:$m254:$m243:$m242:$patch:$gate:$old_gate:$video:$root/m190_mage_runtime:$text/runtime
  export M200_STATIC_ROOT=$m254/static
  export M254_M243_RESULT=$m254/M243_WEB_PREFILL_BOARD_RESULT_05.json
  export M254_M253_RESULT=$m254/M253_KV260_LATEST_FAST_STREAM_BOARD_RESULT_02.json
  export M254_M249_RESULT=$m254/M249_KV260_SSDLITE_BOARD_RESULT_03.json
  export M254_M249_CANDIDATE=$m249
  nohup "$python" "$m254/m254_video_server.py" \
    --candidate "$video" --text-candidate "$text" --weights-root "$weights" \
    --board-gate "$gate/M223_PREDECESSOR_SUMMARY.json" --host 0.0.0.0 --port 8001 \
    > "$result_dir/restore_m254_service.log" 2>&1 &
  new_pid=$!
  echo "$new_pid" > "$pid_file"
  if ! "$python" "$m254/m254_runtime_ready_probe.py" \
      --manifest-sha256 "$m254_manifest_sha256" --pid "$new_pid" \
      --result "$restore_result" --timeout-seconds 240; then
    kill "$new_pid" 2>/dev/null || true
    wait "$new_pid" 2>/dev/null || true
    rm -f "$pid_file"
    return 1
  fi
  return 0
}

restore_active_m254(){
  local index
  for index in 1 2; do
    echo "M277_RESTORE_ATTEMPT=$index"
    if start_active_m254; then return 0; fi
    sleep 2
  done
  return 1
}

finish(){
  original_rc=$?
  trap - EXIT
  restore_rc=0
  if [[ $service_stopped -eq 1 && $restore_attempted -eq 0 ]]; then
    restore_attempted=1
    set +e
    restore_active_m254
    restore_rc=$?
    set -e
  fi
  echo "__M277_GATE_RC_${original_rc}__"
  echo "__M277_RESTORE_RC_${restore_rc}__"
  if [[ $restore_rc -ne 0 ]]; then exit 97; fi
  exit "$original_rc"
}
trap finish EXIT

[[ $(id -u) -eq 0 ]] || { echo M277_ROOT_REQUIRED >&2; exit 1; }
[[ ! -e $result_dir ]] || { echo M277_RESULT_DIR_ALREADY_EXISTS >&2; exit 1; }
[[ -e $pid_file ]] || { echo M277_ACTIVE_PID_FILE_MISSING >&2; exit 1; }
mkdir -p "$result_dir"
export XILINX_XRT=/usr TMPDIR=/dev/shm PYTHONDONTWRITEBYTECODE=1 TRANSFORMERS_OFFLINE=1 HF_HUB_OFFLINE=1
export PATH=/usr/local/share/pynq-venv/bin:/usr/local/bin:/usr/bin:/bin
export PYTHONPATH=$candidate:$m254:$m243:$m242:$patch:$gate:$old_gate:$video:$root/m190_mage_runtime:$text/runtime

observed_m270=$(sha256sum "$candidate/M270_M269_MEMORY_HEADROOM_BOARD_RESULT_01.json")
[[ ${observed_m270%% *} == "$m270_sha256" ]] || { echo M277_M270_HASH_MISMATCH >&2; exit 1; }
"$python" "$candidate/m277_verify_package.py" \
  --root "$candidate" --expected-manifest-sha256 "$manifest_sha256" --runtime-imports
"$python" "$text/runtime/m120_board_env_preflight.py" \
  --candidate "$text" \
  --expected-package-manifest-sha256 406dcca340e4604baeb761445795391c43ec26bd99fa06ffae893d597b17414f \
  --result "$result_dir/environment.json"

[[ -d $torchvision_site/torchvision ]] || { echo M277_TORCHVISION_SITE_MISSING >&2; exit 1; }
PYTHONPATH=$torchvision_site:$m254:$m243:$m242:$patch:$gate:$old_gate:$video:$root/m190_mage_runtime:$text/runtime \
  "$python" "$m254/verify_m254_candidate.py" --root "$m254" --expected-manifest-sha256 "$m254_manifest_sha256"
PYTHONPATH=$torchvision_site:$m254:$m243:$m242:$patch:$gate:$old_gate:$video:$root/m190_mage_runtime:$text/runtime \
  M254_M243_RESULT=$m254/M243_WEB_PREFILL_BOARD_RESULT_05.json \
  M254_M253_RESULT=$m254/M253_KV260_LATEST_FAST_STREAM_BOARD_RESULT_02.json \
  M254_M249_RESULT=$m254/M249_KV260_SSDLITE_BOARD_RESULT_03.json \
  "$python" "$m254/m254_dependency_preflight.py" \
  --candidate "$m254" --m249-candidate "$m249" --result "$result_dir/restore_dependency_preflight.json"

old_pid=$(tr -dc '0-9' < "$pid_file")
[[ -n $old_pid && -r /proc/$old_pid/cmdline ]] || { echo M277_ACTIVE_PROCESS_MISSING >&2; exit 1; }
old_command=$(tr '\0' ' ' < "/proc/$old_pid/cmdline")
[[ $old_command == *m254_dual_path_web_candidate/m254_video_server.py* && $old_command == *"--port 8001"* ]] || {
  echo "M277_REFUSE_UNKNOWN_PROCESS=$old_command" >&2; exit 1;
}
kill "$old_pid"
for _ in $(seq 1 60); do if ! kill -0 "$old_pid" 2>/dev/null; then break; fi; sleep 0.25; done
if kill -0 "$old_pid" 2>/dev/null; then echo M277_ACTIVE_STOP_TIMEOUT >&2; exit 1; fi
service_stopped=1

set +e
"$python" "$candidate/m277_fixed_window_gate.py" \
  --candidate "$video" --text-candidate "$text" --weights-root "$weights" \
  --board-gate "$gate/M223_PREDECESSOR_SUMMARY.json" --fixture-root "$fixtures" \
  --m244-baseline "$candidate/M244_M243_FIXED_FOUR_FRAME_BOARD_RESULT_02.json" \
  --package-manifest-sha256 "$manifest_sha256" --result "$formal"
gate_rc=$?
set -e

restore_attempted=1
set +e
restore_active_m254
restore_rc=$?
set -e
if [[ $restore_rc -eq 0 ]]; then service_stopped=0; fi
echo "__M277_GATE_RC_${gate_rc}__"
echo "__M277_RESTORE_RC_${restore_rc}__"
[[ $restore_rc -eq 0 ]] || exit 97
[[ $gate_rc -eq 0 ]] || exit "$gate_rc"
echo M277_M276_FIXED_WINDOW_RUNNER_PASS
