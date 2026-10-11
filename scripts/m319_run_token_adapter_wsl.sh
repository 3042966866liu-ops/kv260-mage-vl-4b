#!/usr/bin/env bash
set -euo pipefail
workspace=/mnt/c/Users/30429/Desktop/TeLLMe_FPGA_2026
export PYTHONDONTWRITEBYTECODE=1
export PYTHONPATH="${workspace}"
export HF_HUB_OFFLINE=1
export TRANSFORMERS_OFFLINE=1
export OPENBLAS_NUM_THREADS=1
exec /home/lyy/projects/qwen_baseline/.venv/bin/python -B \
  "${workspace}/scripts/m319_token_adapter_gpu_gate.py" \
  --workspace "${workspace}" --model /home/lyy/models/Mage-VL
