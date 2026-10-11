#!/usr/bin/env bash
set -euo pipefail

workspace=/mnt/c/Users/30429/Desktop/TeLLMe_FPGA_2026
python=/home/lyy/projects/qwen_baseline/.venv/bin/python
export PYTHONDONTWRITEBYTECODE=1
export PYTHONPATH="${workspace}/deployment/mage_vl4b/m261_bounded_cache_source:${workspace}/deployment/mage_vl4b/m260_cached_w4_source:${workspace}/deployment/mage_vl4b/m259_prevision_keyframe_source:${workspace}/deployment/mage_vl4b/m258_vision_state_sweep_source:${workspace}/deployment/mage_vl4b/m257_alarm_keyframe_source:${workspace}/deployment/mage_vl4b/m254_dual_path_web_candidate_r4:${workspace}/deployment/mage_vl4b/m243_web_prefill_source:${workspace}/deployment/mage_vl4b/m241_grouped_gqa_board_candidate:${workspace}/deployment/mage_vl4b/m181_m120_video_board_candidate/text_runtime/runtime:${workspace}/deployment/mage_vl4b/m222_realtime_vision_source:${workspace}/deployment/mage_vl4b/m212_live_stream_source:${workspace}/deployment/mage_vl4b/m197_ps_vision_fp32_block_candidate:${workspace}/deployment/mage_vl4b/m181_m120_video_board_candidate"

exec "${python}" \
  "${workspace}/scripts/m261_gate_budgeted_runtime.py" \
  --workspace "${workspace}" \
  --result "${workspace}/deployment/mage_vl4b/M261_BOUNDED_CACHE_OFFLINE_RESULT.json"
