#!/usr/bin/env bash
set -euo pipefail

root=/home/ubuntu/tellme_m120_m89x2_20260901
gate=$root/m192_gate_v2
candidate=$root/m181_m120_video_board_candidate
m190_result=$gate/M193_PILLOW_RUNTIME_REPAIR_RESULT_01.json
result=$root/results/M192_M181_PS_VISION_BOARD_RESULT_02.json

finish() {
  rc=$?
  trap - EXIT
  echo "__M192_PS_VISION_RUNNER_RC_${rc}__"
  exit "$rc"
}
trap finish EXIT

if [[ $(id -u) -ne 0 ]]; then
  echo M192_ROOT_REQUIRED >&2
  exit 1
fi
if [[ -z ${M192_EXPECTED_M190_SHA256:-} ]]; then
  echo M192_EXPECTED_M190_SHA256_REQUIRED >&2
  exit 1
fi
export PYTHONDONTWRITEBYTECODE=1
export PYTHONPATH=$root/m190_mage_runtime
export TRANSFORMERS_OFFLINE=1
export HF_HUB_OFFLINE=1
/usr/local/share/pynq-venv/bin/python "$gate/m192_video_ps_vision_board_gate.py" \
  --candidate "$candidate" \
  --m184-result "$gate/M184_M181_VIDEO_BOARD_IMPORT_RESULT_01.json" \
  --m190-result "$m190_result" \
  --expected-m190-sha256 "$M192_EXPECTED_M190_SHA256" \
  --result "$result"
echo M192_M181_PS_VISION_RUNNER_PASS
