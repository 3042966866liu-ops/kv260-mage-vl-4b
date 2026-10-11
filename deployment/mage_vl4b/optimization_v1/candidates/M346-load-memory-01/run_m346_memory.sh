#!/usr/bin/env bash
set -euo pipefail
package_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$package_dir"
manifest_sha=${1:?exact manifest SHA required}
printf '%s  PACKAGE_MANIFEST.json\n' "$manifest_sha" | sha256sum -c -
sha256sum -c SHA256SUMS
sudo -n true
set +e
sudo -n env XILINX_XRT=/usr TMPDIR=/dev/shm PATH=/usr/local/share/pynq-venv/bin:/usr/local/bin:/usr/bin:/bin PYTHONDONTWRITEBYTECODE=1 TRANSFORMERS_OFFLINE=1 HF_HUB_OFFLINE=1 \
  /usr/local/share/pynq-venv/bin/python3 -B "$package_dir/m346_load_memory_probe.py" "$manifest_sha"
gate_rc=$?
set -e
printf 'M346_MEMORY_DONE gate_rc=%s\n' "$gate_rc"
exit "$gate_rc"
