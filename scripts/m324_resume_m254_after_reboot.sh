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
m249=$root/m249_ssdlite_board_candidate
torchvision_site=/dev/shm/tellme_m254_torchvision
pid_file=$root/results/m223_realtime_service.pid
result_dir=$root/results/m324_m254_resume_after_reboot_01
python=/usr/local/share/pynq-venv/bin/python
manifest_sha256=2a3b720441be44eecc18d57e5d78a8a0a3deab1f8897ee1fb5de02a92c8901a9

[[ $(id -u) -eq 0 ]] || { echo M324_ROOT_REQUIRED >&2; exit 1; }
[[ ! -e $result_dir ]] || { echo M324_RESULT_EXISTS >&2; exit 1; }
[[ -f $pid_file ]] || { echo M324_PID_FILE_MISSING >&2; exit 1; }
[[ -d $torchvision_site/torchvision ]] || { echo M324_TORCHVISION_MISSING >&2; exit 1; }
old_pid=$(tr -dc '0-9' < "$pid_file")
if [[ -n $old_pid && -r /proc/$old_pid/cmdline ]]; then
  echo M324_REFUSE_LIVE_SAVED_PID >&2
  exit 1
fi
[[ -z $(ss -H -lnt '( sport = :8001 )') ]] || { echo M324_REFUSE_PORT_8001_OCCUPIED >&2; exit 1; }

mkdir -p "$result_dir"
export XILINX_XRT=/usr TMPDIR=/dev/shm PYTHONDONTWRITEBYTECODE=1 TRANSFORMERS_OFFLINE=1 HF_HUB_OFFLINE=1
export PATH=/usr/local/share/pynq-venv/bin:/usr/local/bin:/usr/bin:/bin
export PYTHONPATH=$torchvision_site:$candidate:$m243:$m242:$patch:$gate:$old_gate:$video:$root/m190_mage_runtime:$text/runtime
export M200_STATIC_ROOT=$candidate/static
export M254_M243_RESULT=$candidate/M243_WEB_PREFILL_BOARD_RESULT_05.json
export M254_M253_RESULT=$candidate/M253_KV260_LATEST_FAST_STREAM_BOARD_RESULT_02.json
export M254_M249_RESULT=$candidate/M249_KV260_SSDLITE_BOARD_RESULT_03.json
export M254_M249_CANDIDATE=$m249

"$python" "$candidate/verify_m254_candidate.py" --root "$candidate" --expected-manifest-sha256 "$manifest_sha256"
"$python" "$text/runtime/m120_board_env_preflight.py" \
  --candidate "$text" \
  --expected-package-manifest-sha256 406dcca340e4604baeb761445795391c43ec26bd99fa06ffae893d597b17414f \
  --result "$result_dir/environment.json"
"$python" "$candidate/m254_dependency_preflight.py" \
  --candidate "$candidate" --m249-candidate "$m249" --result "$result_dir/dependencies.json"

nohup "$python" "$candidate/m254_video_server.py" \
  --candidate "$video" --text-candidate "$text" --weights-root "$weights" \
  --board-gate "$gate/M223_PREDECESSOR_SUMMARY.json" --host 0.0.0.0 --port 8001 \
  > "$result_dir/service.log" 2>&1 &
new_pid=$!
echo "$new_pid" > "$pid_file"
if ! "$python" "$candidate/m254_runtime_ready_probe.py" \
    --manifest-sha256 "$manifest_sha256" --pid "$new_pid" \
    --result "$result_dir/ready.json" --timeout-seconds 240; then
  kill "$new_pid" 2>/dev/null || true
  wait "$new_pid" 2>/dev/null || true
  echo "$old_pid" > "$pid_file"
  echo M324_M254_RESUME_FAIL >&2
  exit 1
fi
echo M324_M254_RESUME_PASS
