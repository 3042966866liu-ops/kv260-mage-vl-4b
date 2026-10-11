#!/usr/bin/env bash
set -euo pipefail

root=/home/ubuntu/tellme_m120_m89x2_20260901
gate=$root/m222_decoder_microgate
video=$root/m181_m120_video_board_candidate
m218=$root/m218_dual_source_delta
runtime=$root/m190_mage_runtime
result=$gate/M222_ARM64_DECODER_BOARD_RESULT_01.json
manifest_sha256=${1:?M222 package manifest SHA-256 required}

finish() {
  rc=$?
  trap - EXIT
  echo "__M222_RUNNER_RC_${rc}__"
  exit "$rc"
}
trap finish EXIT

[[ ! -e $result ]] || { echo M222_FORMAL_RESULT_ALREADY_EXISTS >&2; exit 1; }
export PYTHONDONTWRITEBYTECODE=1
export PYTHONPATH=$gate:$m218:$video:$runtime

/usr/local/share/pynq-venv/bin/python "$gate/m222_verify_board_delta.py" \
  --root "$gate" --expected-manifest-sha256 "$manifest_sha256"
/usr/local/share/pynq-venv/bin/python "$gate/m222_board_decode_microbench.py" \
  --layout "$video/vision_layout" --result "$result"
echo M222_ARM64_DECODER_RUNNER_PASS
