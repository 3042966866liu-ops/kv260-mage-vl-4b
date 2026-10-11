#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")"
manifest_sha=${1:?manifest SHA required}
[[ "${2:-}" == "--enable-device-phase-probe" ]] || { echo M355_DISABLED; exit 2; }
printf '%s  PACKAGE_MANIFEST.json\n' "$manifest_sha" | sha256sum -c -
sha256sum -c SHA256SUMS
sudo -n true
[[ ! -e /home/ubuntu/m355_device_phase_evidence_01 ]] || { echo M355_EXISTS_COLLECT_ONLY; exit 2; }
set +e
sudo -n env XILINX_XRT=/usr TMPDIR=/dev/shm PATH=/usr/local/share/pynq-venv/bin:/usr/local/bin:/usr/bin:/bin PYTHONDONTWRITEBYTECODE=1 /usr/local/share/pynq-venv/bin/python3 -B ./m355_device_phase_probe.py "$manifest_sha" --enable-device-phase-probe
gate_rc=$?
sudo -n /usr/local/share/pynq-venv/bin/python3 -B ./m355_export_result.py
export_rc=$?
set -e
printf 'M355_DONE gate_rc=%s export_rc=%s\n' "$gate_rc" "$export_rc"
if [[ "$gate_rc" -ne 0 ]]; then exit "$gate_rc"; fi
exit "$export_rc"
