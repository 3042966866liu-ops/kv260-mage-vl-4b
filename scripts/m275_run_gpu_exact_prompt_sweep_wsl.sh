#!/usr/bin/env bash
set -euo pipefail

workspace=/mnt/c/Users/30429/Desktop/TeLLMe_FPGA_2026
python=/home/lyy/projects/qwen_baseline/.venv/bin/python
export PYTHONDONTWRITEBYTECODE=1
export PYTHONPATH="${workspace}/scripts:${workspace}/deployment/mage_vl4b/m273_latest_binary_source:${workspace}/deployment/mage_vl4b/m246_knife_binary_source"

exec "${python}" \
  "${workspace}/scripts/m275_gpu_exact_prompt_sweep.py" \
  --workspace "${workspace}" \
  --model /home/lyy/models/Mage-VL \
  --examples /home/lyy/models/Mage-VL/examples \
  --m273 "${workspace}/deployment/mage_vl4b/M273_GPU_EXACT_LATEST_BINARY_RESULT.json" \
  --result "${workspace}/deployment/mage_vl4b/M275_GPU_EXACT_PROMPT_SWEEP_RESULT.json"
