#!/usr/bin/env bash
set -euo pipefail
package_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$package_dir"
level=${1:?single-descriptor or single-chain required}
[[ $level == single-descriptor || $level == single-chain ]] || exit 2
manifest_sha=${2:?exact package SHA required}
printf '%s  PACKAGE_MANIFEST.json\n' "$manifest_sha" | sha256sum -c -
sha256sum -c SHA256SUMS
sudo -n true
extra=()
if [[ $level == single-chain ]]; then extra=(--previous-sha "${3:?exact PASS descriptor SHA required}"); fi
set +e
sudo -n env XILINX_XRT=/usr TMPDIR=/dev/shm PATH=/usr/local/share/pynq-venv/bin:/usr/local/bin:/usr/bin:/bin PYTHONDONTWRITEBYTECODE=1 \
  /usr/local/share/pynq-venv/bin/python3 -B "$package_dir/m342_prefetch_fixture_gate.py" "$level" "$manifest_sha" "${extra[@]}"
gate_rc=$?
set -e
printf 'M342_FIXTURE_DONE level=%s gate_rc=%s\n' "$level" "$gate_rc"
exit "$gate_rc"
