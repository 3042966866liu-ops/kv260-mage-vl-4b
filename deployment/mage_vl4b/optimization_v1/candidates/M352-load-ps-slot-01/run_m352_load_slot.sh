#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")"
manifest_sha=${1:?exact manifest SHA required}
[[ "${2:-}" == "--enable-load-only" ]] || { echo M352_DISABLED_BY_DEFAULT; exit 2; }
printf '%s  PACKAGE_MANIFEST.json\n' "$manifest_sha" | sha256sum -c -
sha256sum -c SHA256SUMS
sudo -n true
[[ ! -e /home/ubuntu/m352_load_memory_evidence_01 ]] || { echo M352_RESULT_EXISTS_COLLECT_ONLY; exit 2; }
set +e
sudo -n env XILINX_XRT=/usr TMPDIR=/dev/shm PATH=/usr/local/share/pynq-venv/bin:/usr/local/bin:/usr/bin:/bin PYTHONDONTWRITEBYTECODE=1 TRANSFORMERS_OFFLINE=1 HF_HUB_OFFLINE=1 /usr/local/share/pynq-venv/bin/python3 -B ./m352_load_ps_slot_probe.py "$manifest_sha" --enable-load-only
gate_rc=$?
sudo -n /usr/local/share/pynq-venv/bin/python3 -B ./m352_export_result.py
export_rc=$?
set -e
printf 'M352_DONE gate_rc=%s export_rc=%s\n' "$gate_rc" "$export_rc"
if [[ "$gate_rc" -ne 0 ]]; then exit "$gate_rc"; fi
exit "$export_rc"
