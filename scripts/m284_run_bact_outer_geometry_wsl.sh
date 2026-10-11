#!/usr/bin/env bash
set -euo pipefail

workspace=/mnt/c/Users/30429/Desktop/TeLLMe_FPGA_2026
python=/home/lyy/projects/qwen_baseline/.venv/bin/python
export PYTHONDONTWRITEBYTECODE=1
export PYTHONPATH="${workspace}/deployment/mage_vl4b/m284_bact_outer_boundaries_source:${workspace}/deployment/mage_vl4b/m276_short_prompt_source:${workspace}/deployment/mage_vl4b/m273_latest_binary_source"

"${python}" -c \
  "import m284_outer_boundary_contract, m276_prompt_contract, m273_latest_multiscale_contract; print('M284_IMPORT_PREFLIGHT_PASS')"

exec "${python}" \
  "${workspace}/scripts/m284_gate_bact_outer_boundary_geometry.py" \
  --workspace "${workspace}" \
  --result "${workspace}/deployment/mage_vl4b/M284_BACT_OUTER_BOUNDARY_GEOMETRY_RESULT.json"
