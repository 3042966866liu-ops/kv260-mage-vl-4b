#!/usr/bin/env bash
set -euo pipefail

variant=${1:?baseline or candidate required}
[[ $variant == baseline || $variant == candidate ]] || { echo M332_VARIANT_INVALID >&2; exit 2; }
mode=${2:-full}
[[ $mode == full || $mode == preflight ]] || { echo M332_MODE_INVALID >&2; exit 2; }
preflight_only=0
result_scope=results
if [[ $mode == preflight ]]; then preflight_only=1; result_scope=preflight; fi
package_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$package_dir"
sha256sum -c SHA256SUMS
sudo -n true
[[ ! -e "$result_scope/$variant/result.json" ]] || { echo M332_RESULT_ALREADY_EXISTS >&2; exit 2; }

set +e
sudo -n env M332_VARIANT="$variant" M332_PREFLIGHT_ONLY="$preflight_only" \
  /usr/local/share/pynq-venv/bin/python3 "$package_dir/run_fixed_video_ab.py"
gate_rc=$?
set -e
if [[ -f "$result_scope/$variant/result.json" ]]; then
  sha256sum "$result_scope/$variant/result.json"
  if [[ -f "$result_scope/$variant/m277_fixed_video.json" ]]; then
    sha256sum "$result_scope/$variant/m277_fixed_video.json"
  fi
  if [[ -f "$result_scope/$variant/video_forward.log" ]]; then
    sha256sum "$result_scope/$variant/video_forward.log"
  fi
fi
printf 'M332_VIDEO_VARIANT_DONE variant=%s mode=%s gate_rc=%s\n' "$variant" "$mode" "$gate_rc"
exit "$gate_rc"
