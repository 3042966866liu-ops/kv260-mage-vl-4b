#!/usr/bin/env bash
set -euo pipefail

workspace=/mnt/c/Users/30429/Desktop/TeLLMe_FPGA_2026
python=/home/lyy/projects/qwen_baseline/.venv/bin/python
export PYTHONDONTWRITEBYTECODE=1
export PYTHONPATH="${workspace}:${workspace}/scripts:${workspace}/deployment/mage_vl4b/scripts:${workspace}/deployment/mage_vl4b/m273_latest_binary_source"

"${python}" -c \
  "import m264_gpu_resolution_semantic_suite, m266_gpu_multiscale_semantic_gate, mage_a8_runtime, packed_checkpoint_artifact; print('M307_IMPORT_PREFLIGHT_PASS')"

exec "${python}" \
  "${workspace}/scripts/m307_collect_four_baseline_predictions.py" \
  --workspace "${workspace}" \
  --model /home/lyy/models/Mage-VL \
  --checkpoint /home/lyy/artifacts/tellme-mage-vl/m120-text4b-mixed-w3e-w4h-w4mlpkv-v2 \
  --manifest "${workspace}/data/bact_target_scene/M296_TARGET_SCENE_MANIFEST_DRAFT.json" \
  --geometry "${workspace}/deployment/mage_vl4b/M306_FOUR_BASELINE_PREDICTION_GEOMETRY_RESULT.json" \
  --progress "${workspace}/tmp/m307_predictions_progress.json" \
  --predictions "${workspace}/data/bact_target_scene/M307_FOUR_BASELINE_PREDICTIONS.json" \
  --result "${workspace}/deployment/mage_vl4b/M307_FOUR_BASELINE_PREDICTION_COLLECTION_RESULT.json"
