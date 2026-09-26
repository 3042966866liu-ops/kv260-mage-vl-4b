#!/usr/bin/env bash
set -euo pipefail
[[ $# -eq 7 ]] || { echo 'M238 argument count mismatch' >&2; exit 2; }
base=$1; delta=$2; language=$3; head=$4; result=$5; base_manifest=$6; delta_manifest=$7
root=/home/ubuntu/tellme_m120_m89x2_20260901
patch=$root/m227_runtime_base_patch
gate=$root/m223_realtime_delta
old_gate=$root/m218_dual_source_delta
video=$root/m181_m120_video_board_candidate
text=$root/m175_m120_fixed_text_candidate
weights=$root/m120_fulltext_weights_0x4D395832
service_pid_file=$root/results/m223_realtime_service.pid
service_stopped=0
restored_pid=0

start_service() {
  env PYTHONPATH=$patch:$gate:$old_gate:$video:$root/m190_mage_runtime M200_STATIC_ROOT=$gate/static \
    nohup /usr/local/share/pynq-venv/bin/python "$gate/m222_video_server.py" \
    --candidate "$video" --text-candidate "$text" --weights-root "$weights" \
    --board-gate "$gate/M223_PREDECESSOR_SUMMARY.json" --host 0.0.0.0 --port 8001 \
    > "$root/results/m238_restored_realtime_service.log" 2>&1 &
  restored_pid=$!
  echo "$restored_pid" > "$service_pid_file"
}

probe_service() {
  local output=$1
  for _ in $(seq 1 12); do
    if python3 "$patch/m227_health_probe.py" --url http://127.0.0.1:8001/api/health \
      --patch-manifest-sha256 0bab466470fe09ef1b548921235a365ac3832c6264bf2e3a16ee19a6a3aad13c \
      --pid "$restored_pid" --result "$output"; then return 0; fi
    rm -f "$output"; sleep 5
  done
  return 1
}

finish() {
  rc=$?; trap - EXIT
  if [[ $service_stopped -eq 1 ]]; then
    start_service; service_stopped=0
    if probe_service "$result/service_restored_after_failure.json"; then
      echo M238_SERVICE_RESTORE_AFTER_FAILURE_PASS
    else
      echo M238_SERVICE_RESTORE_AFTER_FAILURE_TIMEOUT >&2
    fi
  fi
  echo "__M238_RUNNER_RC_${rc}__"
  exit "$rc"
}
trap finish EXIT

export XILINX_XRT=/usr TMPDIR=/dev/shm PYTHONDONTWRITEBYTECODE=1
export PATH=/usr/local/share/pynq-venv/bin:/usr/local/bin:/usr/bin:/bin
export PYTHONPATH="$delta:$base/runtime"
[[ $(id -u) -eq 0 ]] || { echo M238_ROOT_REQUIRED >&2; exit 1; }
[[ ! -e $result ]] || { echo M238_RESULT_ALREADY_EXISTS >&2; exit 1; }
[[ -e $service_pid_file ]] || { echo M238_SERVICE_PID_MISSING >&2; exit 1; }
mkdir -p "$result"
python3 "$delta/m230_verify_package.py" --root "$delta" --expected-manifest-sha256 "$delta_manifest"
python3 "$base/runtime/m120_board_env_preflight.py" --candidate "$base" \
  --expected-package-manifest-sha256 "$base_manifest" --result "$result/environment.json"

service_pid=$(tr -dc '0-9' < "$service_pid_file")
[[ -n $service_pid && -r /proc/$service_pid/cmdline ]] || { echo M238_SERVICE_PROCESS_MISSING >&2; exit 1; }
service_command=$(tr '\0' ' ' < "/proc/$service_pid/cmdline")
[[ $service_command == *m223_realtime_delta/m222_video_server.py* && $service_command == *"--port 8001"* ]] || {
  echo "M238_REFUSE_UNKNOWN_SERVICE=$service_command" >&2; exit 1;
}
kill "$service_pid"
for _ in $(seq 1 20); do if ! kill -0 "$service_pid" 2>/dev/null; then break; fi; sleep 0.25; done
if kill -0 "$service_pid" 2>/dev/null; then echo M238_SERVICE_STOP_TIMEOUT >&2; exit 1; fi
service_stopped=1

python3 "$delta/m238_board_gate.py" \
  --overlay "$base/overlay/m120_m89x2_t32.bit" --language "$language" --head "$head" \
  --language-contract "$base/contracts/M126_LANGUAGE_RUNTIME_CONTRACT_RESULT.json" \
  --head-contract "$base/contracts/M126_LMHEAD_RUNTIME_CONTRACT_RESULT.json" \
  --result "$result/family_measurement.json" --tokens 849

start_service; service_stopped=0
if probe_service "$result/service_restored.json"; then
  echo M238_SERVICE_RESTORE_PASS
  echo M238_INPUT_PREFETCH_BOARD_RUNNER_PASS
  exit 0
fi
echo M238_SERVICE_RESTORE_TIMEOUT >&2
exit 1
