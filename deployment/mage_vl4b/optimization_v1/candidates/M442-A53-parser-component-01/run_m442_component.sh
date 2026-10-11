#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")"
manifest_sha=${1:?exact manifest SHA required}
mode=${2:?Run or Collect required}
printf '%s  PACKAGE_MANIFEST.json
' "$manifest_sha" | sha256sum -c -
sha256sum -c SHA256SUMS
sudo -n true
[[ "$mode" == Run || "$mode" == Collect ]] || exit 2
set +e
if [[ "$mode" == Run ]]; then
 /usr/local/share/pynq-venv/bin/python -B ./m442_component_gate01.py Run "$manifest_sha" --enable-cpu-component
else
 /usr/local/share/pynq-venv/bin/python -B ./m442_component_gate01.py Collect
fi
gate_rc=$?
set -e
printf 'M442C_DONE gate_rc=%s export_rc=0
' "$gate_rc"
exit "$gate_rc"
