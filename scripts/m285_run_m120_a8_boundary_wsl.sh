#!/usr/bin/env bash
set -euo pipefail

workspace=/mnt/c/Users/30429/Desktop/TeLLMe_FPGA_2026
python=/home/lyy/projects/qwen_baseline/.venv/bin/python
export PYTHONDONTWRITEBYTECODE=1
export PYTHONPATH="${workspace}/scripts:${workspace}/deployment/mage_vl4b/scripts:${workspace}/deployment/mage_vl4b/m281_bact_boundary_source:${workspace}/deployment/mage_vl4b/m276_short_prompt_source:${workspace}/deployment/mage_vl4b/m273_latest_binary_source:${workspace}/deployment/mage_vl4b/m246_knife_binary_source"

"${python}" -c \
  "import m264_gpu_resolution_semantic_suite, m281_boundary_contract, m273_latest_multiscale_contract, m246_knife_binary, mage_a8_runtime, packed_checkpoint_artifact; print('M285_IMPORT_PREFLIGHT_PASS')"

exec "${python}" \
  "${workspace}/scripts/m285_m120_a8_boundary_diagnostic.py" \
  --workspace "${workspace}" \
  --model /home/lyy/models/Mage-VL \
  --checkpoint /home/lyy/artifacts/tellme-mage-vl/m120-text4b-mixed-w3e-w4h-w4mlpkv-v2 \
  --examples /home/lyy/models/Mage-VL/examples \
  --result "${workspace}/deployment/mage_vl4b/M285_M120_A8_BOUNDARY_DIAGNOSTIC_RESULT.json"
