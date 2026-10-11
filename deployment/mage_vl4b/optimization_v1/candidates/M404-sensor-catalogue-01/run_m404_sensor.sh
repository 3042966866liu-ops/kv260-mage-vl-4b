#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")"
manifest_sha=${1:?manifest SHA}
mode=${2:?Run or Collect}
if [[ "$mode" == Collect ]]; then
 exec /usr/local/share/pynq-venv/bin/python -B ./m404_sensor_inventory.py Collect
fi
[[ "$mode" == Run && "${M404_ENABLE_READONLY_SENSOR:-0}" == 1 ]] || exit 2
printf '%s  PACKAGE_MANIFEST.json\n' "$manifest_sha" | sha256sum -c -
sha256sum -c SHA256SUMS
exec /usr/local/share/pynq-venv/bin/python -B ./m404_sensor_inventory.py "$manifest_sha" --enable-readonly-catalogue
