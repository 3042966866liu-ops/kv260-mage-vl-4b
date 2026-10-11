#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")"
manifest_sha=${1:?manifest SHA required}
mode=${2:?Run or Collect required}
if [[ "$mode" == Collect ]]; then
  exec /usr/local/share/pynq-venv/bin/python -B ./m404_environment_probe.py Collect
fi
[[ "$mode" == Run && "${M404_ENABLE_READONLY_ENV:-0}" == 1 ]] || exit 2
printf '%s  PACKAGE_MANIFEST.json\n' "$manifest_sha" | sha256sum -c -
sha256sum -c SHA256SUMS
[[ ! -e /home/ubuntu/m404_environment_observation_01 ]] || exit 2
exec /usr/local/share/pynq-venv/bin/python -B ./m404_environment_probe.py "$manifest_sha" --enable-readonly-observation
