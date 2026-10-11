#!/usr/bin/env bash
set -euo pipefail
workspace=/mnt/c/Users/30429/Desktop/TeLLMe_FPGA_2026
export PYTHONDONTWRITEBYTECODE=1 HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 OPENBLAS_NUM_THREADS=1
exec /home/lyy/projects/qwen_baseline/.venv/bin/python -B "$workspace/scripts/optimization/op01_software_reference.py" \
  --model /home/lyy/models/Mage-VL \
  --checkpoint /home/lyy/artifacts/tellme-mage-vl/m120-text4b-mixed-w3e-w4h-w4mlpkv-v2 --mode official
