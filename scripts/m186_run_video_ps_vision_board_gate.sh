#!/usr/bin/env bash
set -euo pipefail

root=/home/ubuntu/tellme_m120_m89x2_20260901
gate=$root/m186_gate
candidate=$root/m181_m120_video_board_candidate
result=$root/results/M186_M181_PS_VISION_BOARD_RESULT.json
selected=

finish() {
  rc=$?
  trap - EXIT
  echo "__M186_PS_VISION_RUNNER_RC_${rc}__"
  exit "$rc"
}
trap finish EXIT

if [[ $(id -u) -ne 0 ]]; then
  echo M186_ROOT_REQUIRED >&2
  exit 1
fi
export PYTHONDONTWRITEBYTECODE=1
for candidate_python in /usr/bin/python3 /usr/local/share/pynq-venv/bin/python3 /usr/local/share/pynq-venv/bin/python; do
  if [[ -x $candidate_python ]] && "$candidate_python" -c 'import numpy,platform,torch,sys; raise SystemExit(0 if platform.machine().lower() in {"aarch64","arm64"} else 1)'; then
    selected=$candidate_python
    break
  fi
done
if [[ -z $selected ]]; then
  echo M186_AARCH64_TORCH_ENVIRONMENT_NOT_FOUND >&2
  exit 1
fi
echo "M186_PS_VISION_PYTHON_SELECTED path=$selected"
"$selected" "$gate/m186_video_ps_vision_board_gate.py" \
  --candidate "$candidate" \
  --m184-result "$gate/M184_M181_VIDEO_BOARD_IMPORT_RESULT_01.json" \
  --result "$result"
echo M186_M181_PS_VISION_RUNNER_PASS
