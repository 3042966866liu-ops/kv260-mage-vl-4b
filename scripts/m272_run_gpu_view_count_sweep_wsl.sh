#!/usr/bin/env bash
set -euo pipefail

workspace=/mnt/c/Users/30429/Desktop/TeLLMe_FPGA_2026
python=/home/lyy/projects/qwen_baseline/.venv/bin/python
export PYTHONDONTWRITEBYTECODE=1
export PYTHONPATH="${workspace}/scripts:${workspace}/deployment/mage_vl4b/m246_knife_binary_source"

exec "${python}" \
  "${workspace}/scripts/m272_gpu_view_count_sweep.py" \
  --workspace "${workspace}" \
  --model /home/lyy/models/Mage-VL \
  --examples /home/lyy/models/Mage-VL/examples \
  --m267 "${workspace}/deployment/mage_vl4b/M267_GPU_BINARY_MULTISCALE_RESULT.json" \
  --result "${workspace}/deployment/mage_vl4b/M272_GPU_VIEW_COUNT_SWEEP_RESULT.json"
