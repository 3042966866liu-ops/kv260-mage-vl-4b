#!/usr/bin/env bash
set -euo pipefail
workspace=/mnt/c/Users/30429/Desktop/TeLLMe_FPGA_2026
export PYTHONDONTWRITEBYTECODE=1
export HF_HUB_OFFLINE=1
export TRANSFORMERS_OFFLINE=1
export OPENBLAS_NUM_THREADS=1
python=/home/lyy/projects/qwen_baseline/.venv/bin/python
runner="${workspace}/scripts/m320_m120_token_adapter_gate.py"
model=/home/lyy/models/Mage-VL
checkpoint=/home/lyy/artifacts/tellme-mage-vl/m120-text4b-mixed-w3e-w4h-w4mlpkv-v2
"${python}" -B "${runner}" --model "${model}" --checkpoint "${checkpoint}" --preflight-only
exec "${python}" -B "${runner}" --model "${model}" --checkpoint "${checkpoint}"
