#!/usr/bin/env bash
set -euo pipefail

root=/home/ubuntu/tellme_m120_m89x2_20260901
package=$root/optimization_v1/OP01-decode-one-sequence-01
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
torchvision_site=/dev/shm/tellme_m254_torchvision
pid_file=$root/results/m223_realtime_service.pid
result_dir=$root/results/m324_decode_sequence_01
python=/usr/local/share/pynq-venv/bin/python
sequence_manifest=21d41a9589bef5bae080ff93ff78f57658766013c076e387bdbda90a1a03d6e0
m254_manifest=2a3b720441be44eecc18d57e5d78a8a0a3deab1f8897ee1fb5de02a92c8901a9
service_stopped=0
restore_attempted=0
new_pid=0

restore_m254(){
  export PYTHONPATH=$torchvision_site:$m254:$m243:$m242:$patch:$gate:$old_gate:$video:$root/m190_mage_runtime:$text/runtime
  export M200_STATIC_ROOT=$m254/static
  export M254_M243_RESULT=$m254/M243_WEB_PREFILL_BOARD_RESULT_05.json
  export M254_M253_RESULT=$m254/M253_KV260_LATEST_FAST_STREAM_BOARD_RESULT_02.json
  export M254_M249_RESULT=$m254/M249_KV260_SSDLITE_BOARD_RESULT_03.json
  export M254_M249_CANDIDATE=$m249
  nohup "$python" "$m254/m254_video_server.py" \
    --candidate "$video" --text-candidate "$text" --weights-root "$weights" \
    --board-gate "$gate/M223_PREDECESSOR_SUMMARY.json" --host 0.0.0.0 --port 8001 \
    > "$result_dir/restore_service.log" 2>&1 &
  new_pid=$!
  echo "$new_pid" > "$pid_file"
  if ! "$python" "$m254/m254_runtime_ready_probe.py" \
      --manifest-sha256 "$m254_manifest" --pid "$new_pid" \
      --result "$result_dir/restore_ready.json" --timeout-seconds 240; then
    kill "$new_pid" 2>/dev/null || true
    wait "$new_pid" 2>/dev/null || true
    return 1
  fi
  return 0
}

finish(){
  original_rc=$?
  trap - EXIT
  restore_rc=0
  if [[ $service_stopped -eq 1 && $restore_attempted -eq 0 ]]; then
    restore_attempted=1
    set +e
    restore_m254
    restore_rc=$?
    set -e
  fi
  echo "__M324_SEQUENCE_RC_${original_rc}__"
  echo "__M324_RESTORE_RC_${restore_rc}__"
  [[ $restore_rc -eq 0 ]] || exit 97
  exit "$original_rc"
}
trap finish EXIT

[[ $(id -u) -eq 0 ]] || { echo M324_ROOT_REQUIRED >&2; exit 1; }
[[ ! -e $result_dir ]] || { echo M324_RESULT_DIR_EXISTS >&2; exit 1; }
[[ -d $package && -f $package/PACKAGE_MANIFEST.json ]] || { echo M324_SEQUENCE_PACKAGE_MISSING >&2; exit 1; }
[[ -d $torchvision_site/torchvision ]] || { echo M324_TORCHVISION_MISSING >&2; exit 1; }
[[ -f $pid_file ]] || { echo M324_ACTIVE_PID_FILE_MISSING >&2; exit 1; }
mkdir -p "$result_dir"
export XILINX_XRT=/usr TMPDIR=/dev/shm PYTHONDONTWRITEBYTECODE=1 TRANSFORMERS_OFFLINE=1 HF_HUB_OFFLINE=1
export PATH=/usr/local/share/pynq-venv/bin:/usr/local/bin:/usr/bin:/bin
"$python" -B "$m254/verify_m254_candidate.py" --root "$m254" --expected-manifest-sha256 "$m254_manifest"

# Imports, recursive package hashes and the real KV852 checkpoint are checked
# before stopping the original Web service or loading an overlay.
bash "$package/run_layer.sh" --mode stable --manifest-sha256 "$sequence_manifest" \
  --result "$result_dir/stable_import.json" --imports-only
bash "$package/run_layer.sh" --mode candidate --manifest-sha256 "$sequence_manifest" \
  --result "$result_dir/candidate_import.json" --imports-only

old_pid=$(tr -dc '0-9' < "$pid_file")
[[ -n $old_pid && -r /proc/$old_pid/cmdline ]] || { echo M324_ACTIVE_PROCESS_MISSING >&2; exit 1; }
old_command=$(tr '\0' ' ' < "/proc/$old_pid/cmdline")
[[ $old_command == *m254_dual_path_web_candidate/m254_video_server.py* && $old_command == *"--port 8001"* ]] || {
  echo "M324_REFUSE_UNKNOWN_PROCESS=$old_command" >&2; exit 1;
}
kill "$old_pid"
for _ in $(seq 1 60); do if ! kill -0 "$old_pid" 2>/dev/null; then break; fi; sleep 0.25; done
if kill -0 "$old_pid" 2>/dev/null; then echo M324_ACTIVE_STOP_TIMEOUT >&2; exit 1; fi
service_stopped=1

bash "$package/run_layer.sh" --mode stable --manifest-sha256 "$sequence_manifest" \
  --result "$result_dir/stable.json"
stable_sha=$(sha256sum "$result_dir/stable.json")
stable_sha=${stable_sha%% *}
echo "M324_STABLE_SEQUENCE_REFERENCE_SHA=$stable_sha"
bash "$package/run_layer.sh" --mode candidate --manifest-sha256 "$sequence_manifest" \
  --reference "$result_dir/stable.json" --reference-sha256 "$stable_sha" \
  --result "$result_dir/candidate.json"

restore_attempted=1
set +e
restore_m254
restore_rc=$?
set -e
echo "__M324_SEQUENCE_RC_0__"
echo "__M324_RESTORE_RC_${restore_rc}__"
[[ $restore_rc -eq 0 ]] || exit 97
service_stopped=0
echo M324_DECODE_SEQUENCE_RUNNER_PASS
