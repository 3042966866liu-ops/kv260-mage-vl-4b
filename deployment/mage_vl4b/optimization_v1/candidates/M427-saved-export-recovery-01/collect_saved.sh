#!/usr/bin/env bash
set -euo pipefail
[[ $EUID == 0 ]] || exit 65
cd "$(dirname "${BASH_SOURCE[0]}")"
task_manifest=${1:?manifest}
printf '%s  PACKAGE_MANIFEST.json\n' "$task_manifest" | sha256sum -c -
sha256sum -c SHA256SUMS
exec /usr/local/share/pynq-venv/bin/python -B ./m427_export_saved02.py
