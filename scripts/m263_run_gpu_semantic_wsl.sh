#!/usr/bin/env bash
set -euo pipefail

workspace=/mnt/c/Users/30429/Desktop/TeLLMe_FPGA_2026
python=/home/lyy/projects/qwen_baseline/.venv/bin/python
export PYTHONDONTWRITEBYTECODE=1

exec "${python}" \
  "${workspace}/scripts/m263_gpu_resolution_semantic_gate.py" \
  --workspace "${workspace}" \
  --model /home/lyy/models/Mage-VL \
  --result "${workspace}/deployment/mage_vl4b/M263_GPU_RESOLUTION_SEMANTIC_RESULT.json"
