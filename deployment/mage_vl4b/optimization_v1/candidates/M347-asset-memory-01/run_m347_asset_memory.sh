#!/usr/bin/env bash
set -euo pipefail
package_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$package_dir"
manifest_sha=${1:?manifest SHA required}
printf '%s  PACKAGE_MANIFEST.json\n' "$manifest_sha" | sha256sum -c -
sha256sum -c SHA256SUMS
sudo -n true
set +e
sudo -n env PYTHONDONTWRITEBYTECODE=1 /usr/local/share/pynq-venv/bin/python3 -B "$package_dir/m347_asset_memory_probe.py" "$manifest_sha"
gate_rc=$?
set -e
printf 'M347_ASSET_DONE gate_rc=%s\n' "$gate_rc"
exit "$gate_rc"
