#!/usr/bin/env bash
set -euo pipefail
root=/home/ubuntu/tellme_m120_m89x2_20260901
gate=$root/m204_gate
text=$root/m175_m120_fixed_text_candidate
result_dir=$root/results/m204_continuous_01
formal=$root/results/M204_CONTINUOUS_VIDEO_BOARD_RESULT_01.json
manifest=406dcca340e4604baeb761445795391c43ec26bd99fa06ffae893d597b17414f
finish(){ rc=$?; trap - EXIT; echo "__M204_CONTINUOUS_RUNNER_RC_${rc}__"; exit "$rc"; }
trap finish EXIT
[[ $(id -u) -eq 0 ]] || exit 1
[[ ! -e $formal ]] || { echo M204_FORMAL_RESULT_ALREADY_EXISTS >&2; exit 1; }
mkdir -p "$result_dir"
export XILINX_XRT=/usr TMPDIR=/dev/shm PYTHONDONTWRITEBYTECODE=1 TRANSFORMERS_OFFLINE=1 HF_HUB_OFFLINE=1
export PATH=/usr/local/share/pynq-venv/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin
export PYTHONPATH=$gate:$root/m181_m120_video_board_candidate:$root/m190_mage_runtime
/usr/local/share/pynq-venv/bin/python "$text/runtime/m120_board_env_preflight.py" --candidate "$text" --expected-package-manifest-sha256 "$manifest" --result "$result_dir/environment.json"
/usr/local/share/pynq-venv/bin/python "$gate/m204_continuous_video_board_gate.py" --gate-root "$gate" --board-gate "$gate/BOARD_GATE_RESULT.json" --m202-result "$gate/M202_M200_FIXED_VIDEO_E2E_BOARD_RESULT_01.json" --environment-result "$result_dir/environment.json" --result "$formal"
echo M204_CONTINUOUS_VIDEO_RUNNER_PASS
