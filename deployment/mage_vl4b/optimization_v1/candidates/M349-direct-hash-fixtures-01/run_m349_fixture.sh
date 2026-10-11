#!/usr/bin/env bash
set -euo pipefail
package_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$package_dir"
manifest_sha=${1:?manifest SHA required}
enable=${2:-}
if [[ "$enable" != "--enable-fixture-gate" ]]; then printf "M349_DISABLED_BY_DEFAULT\n"; exit 2; fi
printf '%s  PACKAGE_MANIFEST.json\n' "$manifest_sha" | sha256sum -c -
sha256sum -c SHA256SUMS
sudo -n true
set +e
sudo -n env PYTHONDONTWRITEBYTECODE=1 /usr/local/share/pynq-venv/bin/python3 -B "$package_dir/m349_direct_hash_fixture_gate.py" "$manifest_sha" --enable-fixture-gate
gate_rc=$?
sudo -n env PYTHONDONTWRITEBYTECODE=1 /usr/local/share/pynq-venv/bin/python3 -B "$package_dir/m349_export_result.py"
export_rc=$?
set -e
printf 'M349_DONE gate_rc=%s export_rc=%s\n' "$gate_rc" "$export_rc"
if [[ "$gate_rc" -ne 0 ]]; then exit "$gate_rc"; fi
exit "$export_rc"
