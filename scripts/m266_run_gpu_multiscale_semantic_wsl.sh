#!/usr/bin/env bash
set -euo pipefail

workspace=/mnt/c/Users/30429/Desktop/TeLLMe_FPGA_2026
python=/home/lyy/projects/qwen_baseline/.venv/bin/python
export PYTHONDONTWRITEBYTECODE=1

exec "${python}" \
  "${workspace}/scripts/m266_gpu_multiscale_semantic_gate.py" \
  --workspace "${workspace}" \
  --model /home/lyy/models/Mage-VL \
  --examples /home/lyy/models/Mage-VL/examples \
  --m264 "${workspace}/deployment/mage_vl4b/M264_GPU_RESOLUTION_SEMANTIC_SUITE_RESULT.json" \
  --m265 "${workspace}/deployment/mage_vl4b/M265_GPU_RESOLUTION_SWEEP_RESULT.json" \
  --result "${workspace}/deployment/mage_vl4b/M266_GPU_MULTISCALE_SEMANTIC_RESULT.json"
