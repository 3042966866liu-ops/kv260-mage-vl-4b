#!/usr/bin/env bash
set -euo pipefail
workspace=/mnt/c/Users/30429/Desktop/TeLLMe_FPGA_2026
python=/home/lyy/projects/qwen_baseline/.venv/bin/python
candidate=${workspace}/deployment/mage_vl4b/m287_natural_prompt_board_candidate
base=${workspace}/deployment/mage_vl4b/m283_bact_boundary_board_candidate
manifest=$("${python}" -c "import json; print(json.load(open('${workspace}/deployment/mage_vl4b/M287_NATURAL_PROMPT_BUILD_RESULT.json'))['manifest_sha256'])")
export PYTHONDONTWRITEBYTECODE=1
export PYTHONPATH="${candidate}:${base}:${workspace}/deployment/mage_vl4b/m254_dual_path_web_candidate_r4:${workspace}/deployment/mage_vl4b/m243_web_prefill_source:${workspace}/deployment/mage_vl4b/m241_grouped_gqa_board_candidate:${workspace}/deployment/mage_vl4b/m181_m120_video_board_candidate/text_runtime/runtime:${workspace}/deployment/mage_vl4b/m222_realtime_vision_source:${workspace}/deployment/mage_vl4b/m212_live_stream_source:${workspace}/deployment/mage_vl4b/m197_ps_vision_fp32_block_candidate:${workspace}/deployment/mage_vl4b/m181_m120_video_board_candidate"
"${python}" "${candidate}/m287_verify_package.py" --root "${candidate}" --expected-manifest-sha256 "${manifest}" --runtime-imports \
  --tokenizer "${workspace}/deployment/mage_vl4b/m181_m120_video_board_candidate/text_auxiliary/tokenizer/tokenizer.json"
bash -n "${candidate}/run_m287_natural_prompt_gate.sh"
echo M287_WSL_RUNTIME_IMPORT_AND_BASH_PASS
