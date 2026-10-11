#!/usr/bin/env bash
set -euo pipefail
package_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$package_dir"
manifest_sha=${1:?exact manifest SHA required}
printf '%s  PACKAGE_MANIFEST.json\n' "$manifest_sha" | sha256sum -c -
sha256sum -c SHA256SUMS
sudo -n true
result=/home/ubuntu/m341_build_id_evidence_01/BOARD_RESULT.json
[[ ! -e "$result" ]] || { echo M341_IMMUTABLE_RESULT_EXISTS >&2; exit 2; }
set +e
sudo -n env XILINX_XRT=/usr TMPDIR=/dev/shm PATH=/usr/local/share/pynq-venv/bin:/usr/local/bin:/usr/bin:/bin PYTHONDONTWRITEBYTECODE=1 \
  /usr/local/share/pynq-venv/bin/python3 -B "$package_dir/m341_build_id_gate.py" --manifest-sha256 "$manifest_sha" --result "$result"
gate_rc=$?
set -e
printf 'M341_BUILD_ID_DONE gate_rc=%s\n' "$gate_rc"
exit "$gate_rc"
