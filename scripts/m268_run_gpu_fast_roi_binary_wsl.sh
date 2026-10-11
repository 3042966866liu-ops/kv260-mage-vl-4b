#!/usr/bin/env bash
set -euo pipefail

workspace=/mnt/c/Users/30429/Desktop/TeLLMe_FPGA_2026
python=/home/lyy/projects/qwen_baseline/.venv/bin/python
export PYTHONDONTWRITEBYTECODE=1

exec "${python}" \
  "${workspace}/scripts/m268_gpu_fast_roi_binary_gate.py" \
  --workspace "${workspace}" \
  --model /home/lyy/models/Mage-VL \
  --examples /home/lyy/models/Mage-VL/examples \
  --m267 "${workspace}/deployment/mage_vl4b/M267_GPU_BINARY_MULTISCALE_RESULT.json" \
  --result "${workspace}/deployment/mage_vl4b/M268_GPU_FAST_ROI_BINARY_RESULT.json"
