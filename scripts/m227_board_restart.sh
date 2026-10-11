#!/usr/bin/env bash
set -euo pipefail

root=/home/ubuntu/tellme_m120_m89x2_20260901
patch=$root/m227_runtime_base_patch
gate=$root/m223_realtime_delta
old_gate=$root/m218_dual_source_delta
video=$root/m181_m120_video_board_candidate
text=$root/m175_m120_fixed_text_candidate
weights=$root/m120_fulltext_weights_0x4D395832
result_dir=$root/results/m227_runtime_base_patch_01
formal=$root/results/M227_RUNTIME_BASE_PATCH_BOARD_RESULT_01.json
current_pid_file=$root/results/m223_realtime_service.pid
old_pid_file=$root/results/m218_dual_source_service.pid
patch_manifest_sha256=${1:?M227 patch manifest SHA-256 required}
current_stopped=0
new_pid=0

rollback_m218() {
  if [[ $new_pid -gt 0 ]] && kill -0 "$new_pid" 2>/dev/null; then kill "$new_pid" 2>/dev/null || true; fi
  if [[ $current_stopped -eq 1 ]]; then
    env PYTHONPATH=$old_gate:$video:$root/m190_mage_runtime M200_STATIC_ROOT=$old_gate/static \
      nohup /usr/local/share/pynq-venv/bin/python "$old_gate/video_server.py" \
      --candidate "$video" --text-candidate "$text" --weights-root "$weights" \
      --board-gate "$old_gate/M218_PREDECESSOR_SUMMARY.json" --host 0.0.0.0 --port 8001 \
      > "$root/results/m218_dual_source_service.log" 2>&1 &
    echo $! > "$old_pid_file"
  fi
}

finish() {
  rc=$?
  trap - EXIT
  if [[ $rc -ne 0 ]]; then rollback_m218; fi
  echo "__M227_RUNNER_RC_${rc}__"
  exit "$rc"
}
trap finish EXIT

[[ $(id -u) -eq 0 ]] || { echo M227_ROOT_REQUIRED >&2; exit 1; }
[[ ! -e $formal ]] || { echo M227_FORMAL_RESULT_ALREADY_EXISTS >&2; exit 1; }
[[ -e $current_pid_file ]] || { echo M227_M223_PID_MISSING >&2; exit 1; }
mkdir -p "$result_dir"
export XILINX_XRT=/usr TMPDIR=/dev/shm PYTHONDONTWRITEBYTECODE=1 TRANSFORMERS_OFFLINE=1 HF_HUB_OFFLINE=1
export PATH=/usr/local/share/pynq-venv/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin
export PYTHONPATH=$patch:$gate:$old_gate:$video:$root/m190_mage_runtime

/usr/local/share/pynq-venv/bin/python "$patch/m227_verify_patch.py" --root "$patch" \
  --expected-manifest-sha256 "$patch_manifest_sha256"
/usr/local/share/pynq-venv/bin/python "$patch/m227_import_preflight.py"

current_pid=$(tr -dc '0-9' < "$current_pid_file")
[[ -r /proc/$current_pid/cmdline ]] || { echo M227_M223_PROCESS_MISSING >&2; exit 1; }
current_command=$(tr '\0' ' ' < "/proc/$current_pid/cmdline")
[[ $current_command == *m223_realtime_delta/m222_video_server.py* && $current_command == *"--port 8001"* ]] || {
  echo "M227_REFUSE_UNKNOWN_PROCESS=$current_command" >&2; exit 1;
}
kill "$current_pid"
for _ in $(seq 1 20); do if ! kill -0 "$current_pid" 2>/dev/null; then break; fi; sleep 0.25; done
if kill -0 "$current_pid" 2>/dev/null; then echo M227_M223_STOP_TIMEOUT >&2; exit 1; fi
mv "$current_pid_file" "$current_pid_file.replaced-by-m227"
current_stopped=1

M200_STATIC_ROOT=$gate/static nohup /usr/local/share/pynq-venv/bin/python \
  "$gate/m222_video_server.py" --candidate "$video" --text-candidate "$text" \
  --weights-root "$weights" --board-gate "$gate/M223_PREDECESSOR_SUMMARY.json" \
  --host 0.0.0.0 --port 8001 > "$root/results/m227_realtime_service.log" 2>&1 &
new_pid=$!
echo "$new_pid" > "$current_pid_file"
/usr/local/share/pynq-venv/bin/python "$patch/m227_health_probe.py" \
  --url http://127.0.0.1:8001/api/health --patch-manifest-sha256 "$patch_manifest_sha256" \
  --pid "$new_pid" --result "$formal"
current_stopped=0
echo M227_RUNTIME_BASE_PATCH_START_PASS

