#!/usr/bin/env bash
set -euo pipefail
[[ $EUID == 0 ]] || exit 65
cd "$(dirname "${BASH_SOURCE[0]}")"
task_manifest=${1:?manifest}
task_mode=${2:?explicit CPU gate or Collect}
printf '%s  PACKAGE_MANIFEST.json\n' "$task_manifest" | sha256sum -c -
sha256sum -c SHA256SUMS
export PYTHONDONTWRITEBYTECODE=1
exec /usr/local/share/pynq-venv/bin/python -I -B ./m431_cpu.py "$task_manifest" "$task_mode"
