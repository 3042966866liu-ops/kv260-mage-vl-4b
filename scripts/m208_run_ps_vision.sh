#!/usr/bin/env bash
set -euo pipefail
root=/home/ubuntu/tellme_m120_m89x2_20260901
gate=$root/m208_gate
text=$root/m175_m120_fixed_text_candidate
result_dir=$root/results/m208_ps_vision_01
formal=$root/results/M208_M207_PS_VISION_BOARD_RESULT_01.json
manifest=406dcca340e4604baeb761445795391c43ec26bd99fa06ffae893d597b17414f
finish(){ rc=$?; trap - EXIT; echo "__M208_PS_VISION_RUNNER_RC_${rc}__"; exit "$rc"; }
trap finish EXIT
[[ $(id -u) -eq 0 ]] || exit 1
[[ ! -e $formal ]] || { echo M208_FORMAL_RESULT_ALREADY_EXISTS >&2; exit 1; }
rm -f "$root/results/M208_M207_PS_VISION_RAW_RESULT.json"
mkdir -p "$result_dir"
export XILINX_XRT=/usr TMPDIR=/dev/shm PYTHONDONTWRITEBYTECODE=1 TRANSFORMERS_OFFLINE=1 HF_HUB_OFFLINE=1
export PATH=/usr/local/share/pynq-venv/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin
export PYTHONPATH=$gate:$root/m190_mage_runtime
/usr/local/share/pynq-venv/bin/python "$text/runtime/m120_board_env_preflight.py" --candidate "$text" --expected-package-manifest-sha256 "$manifest" --result "$result_dir/environment.json"
/usr/local/share/pynq-venv/bin/python "$gate/m208_ps_vision_board_gate.py" --gate-root "$gate" --candidate "$root/m181_m120_video_board_candidate" --m198-result "$gate/M198_M197_PS_VISION_BOARD_RESULT_01.json" --m207-offline-result "$gate/M207_OFFLINE_FP32_GEMM_M198_POLICY_RESULT_ATTEMPT02.json" --environment-result "$result_dir/environment.json" --result "$formal"
echo M208_PS_VISION_RUNNER_PASS

