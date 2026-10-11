#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")"
manifest_sha=${1:?exact SHA required}
mode=${2:?Run or Collect required}
[[ "$EUID" == 0 ]] || exit 2
[[ "$mode" == Run || "$mode" == Collect ]] || exit 2
printf '%s  PACKAGE_MANIFEST.json\n' "$manifest_sha" | sha256sum -c -
sha256sum -c SHA256SUMS
if [[ "$mode" == Run ]]; then
 [[ "${M364_ENABLE_METADATA:-0}" == 1 ]] || exit 2
 [[ ! -e /home/ubuntu/m364_cma_metadata_evidence_01 ]] || { echo M364_COLLECT_ONLY; exit 2; }
 set +e
 PYTHONDONTWRITEBYTECODE=1 /usr/local/share/pynq-venv/bin/python -B ./m364_cma_metadata.py Run "$manifest_sha"
 gate_rc=$?
 set -e
else
 gate_rc=0
fi
set +e
PYTHONDONTWRITEBYTECODE=1 /usr/local/share/pynq-venv/bin/python -B ./m364_cma_metadata.py Collect
export_rc=$?
set -e
if [[ "$mode" == Run ]]; then
 printf 'M364_DONE gate_rc=%s export_rc=%s\n' "$gate_rc" "$export_rc"
fi
[[ "$gate_rc" == 0 ]] || exit "$gate_rc"
exit "$export_rc"
