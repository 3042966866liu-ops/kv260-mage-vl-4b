#!/usr/bin/env bash
set -euo pipefail

root=/home/ubuntu/tellme_m120_m89x2_20260901
m325=$root/optimization_v1/m325_full_session_02
sequence=$root/optimization_v1/OP01-decode-one-sequence-01
m277=$root/m277_m276_fixed_window_candidate
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
result_dir=$root/results/m325_full_session_02
prior_dir=$root/results/m325_full_session_01
python=/usr/local/share/pynq-venv/bin/python
sequence_manifest=21d41a9589bef5bae080ff93ff78f57658766013c076e387bdbda90a1a03d6e0
m277_manifest=0e1bdfa578f655b2bb6d07b097f1dda115a7936906e3e112137123db65e7f2fa
m254_manifest=2a3b720441be44eecc18d57e5d78a8a0a3deab1f8897ee1fb5de02a92c8901a9
stable_manifest=406dcca340e4604baeb761445795391c43ec26bd99fa06ffae893d597b17414f
service_stopped=0
last_result=

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
  "$python" "$m254/m254_runtime_ready_probe.py" \
    --manifest-sha256 "$m254_manifest" --pid "$new_pid" \
    --result "$result_dir/restore_ready.json" --timeout-seconds 240
}

finish(){
  original_rc=$?
  trap - EXIT
  restore_rc=0
  if [[ $service_stopped -eq 1 ]]; then
    if [[ -n $last_result && -f ${last_result%.json}.safe ]]; then
      set +e
      restore_m254
      restore_rc=$?
      set -e
    else
      echo M325_RECOVERY_REQUIRED_LAST_GATE_NOT_SAFE >&2
      restore_rc=98
    fi
  fi
  echo "__M325_GATE_RC_${original_rc}__"
  echo "__M325_RESTORE_RC_${restore_rc}__"
  [[ $restore_rc -eq 0 ]] || exit "$restore_rc"
  exit "$original_rc"
}
trap finish EXIT

[[ $(id -u) -eq 0 ]] || { echo M325_ROOT_REQUIRED >&2; exit 1; }
sudo -n true || { echo M325_SUDO_EXPIRED >&2; exit 1; }
[[ ! -e $result_dir ]] || { echo M325_RESULT_EXISTS >&2; exit 1; }
[[ -d $m325 && -d $sequence && -d $m277 ]] || { echo M325_PACKAGE_MISSING >&2; exit 1; }
[[ -d $torchvision_site/torchvision && -f $pid_file ]] || { echo M325_SERVICE_DEPENDENCY_MISSING >&2; exit 1; }
mkdir -p "$result_dir"
export XILINX_XRT=/usr TMPDIR=/dev/shm PYTHONDONTWRITEBYTECODE=1 TRANSFORMERS_OFFLINE=1 HF_HUB_OFFLINE=1
export OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=4
export PATH=/usr/local/share/pynq-venv/bin:/usr/local/bin:/usr/bin:/bin
export PYTHONPATH=$m325:$m277:$sequence:$torchvision_site:$m254:$m243:$m242:$patch:$gate:$old_gate:$video:$root/m190_mage_runtime:$text/runtime
export M254_M243_RESULT=$m254/M243_WEB_PREFILL_BOARD_RESULT_05.json
export M254_M253_RESULT=$m254/M253_KV260_LATEST_FAST_STREAM_BOARD_RESULT_02.json
export M254_M249_RESULT=$m254/M249_KV260_SSDLITE_BOARD_RESULT_03.json
export M254_M249_CANDIDATE=$m249

# Every check below finishes before the existing Web service is stopped.
(cd "$m325" && sha256sum --check M325_SHA256SUMS.txt)
"$python" -B "$m277/m277_verify_package.py" --root "$m277" \
  --expected-manifest-sha256 "$m277_manifest" --runtime-imports
"$python" -B "$m254/verify_m254_candidate.py" --root "$m254" \
  --expected-manifest-sha256 "$m254_manifest"
"$python" -B "$m254/m254_dependency_preflight.py" --candidate "$m254" \
  --m249-candidate "$m249" --result "$result_dir/m254_dependencies.json"
"$python" -B "$text/runtime/m120_board_env_preflight.py" --candidate "$text" \
  --expected-package-manifest-sha256 "$stable_manifest" --result "$result_dir/stable_environment.json"
"$python" -B "$sequence/decode_one_env_preflight.py" --candidate "$sequence" \
  --expected-package-manifest-sha256 "$sequence_manifest" --result "$result_dir/candidate_environment.json"
"$python" -B "$m325/m325_resume_gate.py" --prior "$prior_dir" \
  --result "$result_dir/reused_text_gate.json"

old_pid=$(tr -dc '0-9' < "$pid_file")
[[ -n $old_pid && -r /proc/$old_pid/cmdline ]] || { echo M325_ACTIVE_PROCESS_MISSING >&2; exit 1; }
old_command=$(tr '\0' ' ' < "/proc/$old_pid/cmdline")
[[ $old_command == *m254_dual_path_web_candidate/m254_video_server.py* && $old_command == *"--port 8001"* ]] || {
  echo "M325_REFUSE_UNKNOWN_PROCESS=$old_command" >&2; exit 1;
}
kill "$old_pid"
for _ in $(seq 1 60); do if ! kill -0 "$old_pid" 2>/dev/null; then break; fi; sleep 0.25; done
if kill -0 "$old_pid" 2>/dev/null; then echo M325_ACTIVE_STOP_TIMEOUT >&2; exit 1; fi
service_stopped=1

run_gate(){
  mode=$1
  scope=$2
  last_result=$result_dir/${scope}_${mode}.json
  reference_args=()
  if [[ $mode == candidate ]]; then reference_args=(--reference "$result_dir/${scope}_stable.json"); fi
  set +e
  "$python" -B "$m325/m325_full_session_board.py" --mode "$mode" --scope "$scope" \
    --result "$last_result" "${reference_args[@]}"
  gate_rc=$?
  set -e
  [[ -f ${last_result%.json}.safe ]] || { echo M325_UNSAFE_OR_INCOMPLETE_GATE >&2; return 98; }
  [[ $gate_rc -eq 0 ]] || return "$gate_rc"
}

run_gate stable video
run_gate candidate video
echo M325_FULL_SESSION_RUNNER_PASS
