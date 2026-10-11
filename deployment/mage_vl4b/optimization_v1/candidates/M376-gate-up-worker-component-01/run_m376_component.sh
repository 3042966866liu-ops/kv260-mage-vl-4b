#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")"
manifest_sha=${1:?exact manifest SHA required}
[[ "${2:-}" == "--enable-fixture-gate" ]] || { echo M376_DISABLED_BY_DEFAULT; exit 2; }
printf '%s  PACKAGE_MANIFEST.json\n' "$manifest_sha" | sha256sum -c -
sha256sum -c SHA256SUMS
sudo -n true
[[ ! -e /home/ubuntu/m376_gate_up_component_evidence_01 ]] || { echo M376_RESULT_EXISTS_COLLECT_ONLY; exit 2; }
set +e
sudo -n env PYTHONDONTWRITEBYTECODE=1 /usr/local/share/pynq-venv/bin/python3 -B ./m376_component_gate.py "$manifest_sha" --enable-fixture-gate
gate_rc=$?
sudo -n env PYTHONDONTWRITEBYTECODE=1 /usr/local/share/pynq-venv/bin/python3 -B ./m376_export_result.py
export_rc=$?
set -e
printf 'M376_DONE gate_rc=%s export_rc=%s\n' "$gate_rc" "$export_rc"
if [[ "$gate_rc" -ne 0 ]]; then exit "$gate_rc"; fi
exit "$export_rc"
