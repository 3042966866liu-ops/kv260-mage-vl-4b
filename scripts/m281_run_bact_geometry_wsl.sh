#!/usr/bin/env bash
set -euo pipefail

workspace=/mnt/c/Users/30429/Desktop/TeLLMe_FPGA_2026
python=/home/lyy/projects/qwen_baseline/.venv/bin/python
export PYTHONDONTWRITEBYTECODE=1
export PYTHONPATH="${workspace}/deployment/mage_vl4b/m281_bact_boundary_source:${workspace}/deployment/mage_vl4b/m276_short_prompt_source:${workspace}/deployment/mage_vl4b/m273_latest_binary_source"

exec "${python}" \
  "${workspace}/scripts/m281_gate_bact_159_160_161_geometry.py" \
  --workspace "${workspace}" \
  --result "${workspace}/deployment/mage_vl4b/M281_BACT_159_160_161_GEOMETRY_RESULT.json"
