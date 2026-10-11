#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")"
mode=${1:?receive or collect required}
digest=${2:?exact bootstrap manifest SHA required}
printf '%s  PACKAGE_MANIFEST.json
' "$digest" | sha256sum -c -
sha256sum -c SHA256SUMS
sudo -n true
exec /usr/local/share/pynq-venv/bin/python -B ./m442_transfer01.py "$mode" . "$digest"
