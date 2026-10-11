#!/usr/bin/env bash
set -euo pipefail

workspace=/mnt/c/Users/30429/Desktop/TeLLMe_FPGA_2026
python=/home/lyy/projects/qwen_baseline/.venv/bin/python
export PYTHONDONTWRITEBYTECODE=1
export PYTHONPATH="${workspace}/scripts:${workspace}/deployment/mage_vl4b/m281_bact_boundary_source:${workspace}/deployment/mage_vl4b/m276_short_prompt_source:${workspace}/deployment/mage_vl4b/m273_latest_binary_source:${workspace}/deployment/mage_vl4b/m246_knife_binary_source"

"${python}" -c \
  "import m264_gpu_resolution_semantic_suite, m281_boundary_contract, m273_latest_multiscale_contract, m246_knife_binary; print('M282_IMPORT_PREFLIGHT_PASS')"

exec "${python}" \
  "${workspace}/scripts/m282_gpu_bact_159_160_161_sweep.py" \
  --workspace "${workspace}" \
  --model /home/lyy/models/Mage-VL \
  --examples /home/lyy/models/Mage-VL/examples \
  --result "${workspace}/deployment/mage_vl4b/M282_GPU_BACT_159_160_161_RESULT.json"
