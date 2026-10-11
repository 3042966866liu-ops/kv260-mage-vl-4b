#!/usr/bin/env bash
set -euo pipefail

root=/home/ubuntu/tellme_m120_m89x2_20260901
gate=$root/m198_gate
candidate=$root/m181_m120_video_board_candidate
result=$root/results/M198_M197_PS_VISION_BOARD_RESULT_01.json

finish() {
  rc=$?
  trap - EXIT
  echo "__M198_PS_VISION_RUNNER_RC_${rc}__"
  exit "$rc"
}
trap finish EXIT

if [[ $(id -u) -ne 0 ]]; then
  echo M198_ROOT_REQUIRED >&2
  exit 1
fi
export PYTHONDONTWRITEBYTECODE=1
export PYTHONPATH=$gate:$root/m190_mage_runtime
export TRANSFORMERS_OFFLINE=1
export HF_HUB_OFFLINE=1
/usr/local/share/pynq-venv/bin/python "$gate/m198_video_ps_vision_board_gate.py" \
  --candidate "$candidate" \
  --m192-result "$gate/M192_M181_PS_VISION_BOARD_RESULT_02.json" \
  --m197-offline-result "$gate/M197_OFFLINE_FP32_LAYERS_06_23.json" \
  --runtime-script "$gate/ps_vision_runtime.py" \
  --test-script "$gate/test_ps_vision_runtime.py" \
  --result "$result"
echo M198_M197_PS_VISION_RUNNER_PASS
