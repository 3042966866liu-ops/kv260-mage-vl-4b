#!/usr/bin/env bash
set -euo pipefail

variant=${1:?baseline or candidate required}
[[ $variant == baseline || $variant == candidate ]] || { echo M332_VARIANT_INVALID >&2; exit 2; }
package_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$package_dir"
sha256sum -c SHA256SUMS
sudo -n true
[[ ! -e "results/$variant/result.json" ]] || { echo M332_RESULT_ALREADY_EXISTS >&2; exit 2; }

set +e
sudo -n env M332_VARIANT="$variant" \
  /usr/local/share/pynq-venv/bin/python3 "$package_dir/run_fixed_video_ab.py"
gate_rc=$?
set -e
if [[ -f "results/$variant/result.json" ]]; then
  sha256sum "results/$variant/result.json"
  if [[ -f "results/$variant/m277_fixed_video.json" ]]; then
    sha256sum "results/$variant/m277_fixed_video.json"
  fi
  if [[ -f "results/$variant/video_forward.log" ]]; then
    sha256sum "results/$variant/video_forward.log"
  fi
fi
printf 'M332_VIDEO_VARIANT_DONE variant=%s gate_rc=%s\n' "$variant" "$gate_rc"
exit "$gate_rc"
