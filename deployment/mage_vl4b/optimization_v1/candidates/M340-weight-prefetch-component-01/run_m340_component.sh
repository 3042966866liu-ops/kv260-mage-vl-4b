#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")"
manifest_sha=${1:?exact manifest hash required}
printf '%s  PACKAGE_MANIFEST.json\n' "$manifest_sha" | sha256sum -c -
sha256sum -c SHA256SUMS
[[ ! -e COMPONENT_RESULT.json ]] || { echo M340_IMMUTABLE_RESULT_EXISTS >&2; exit 2; }
set +e
/usr/local/share/pynq-venv/bin/python3 -B ./m340_component_probe.py "$manifest_sha"
gate_rc=$?
set -e
printf 'M340_CPU_ONLY_DONE gate_rc=%s\n' "$gate_rc"
exit "$gate_rc"
