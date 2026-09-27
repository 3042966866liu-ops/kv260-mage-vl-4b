#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
RELEASE=/home/ubuntu/tellme_release_install_20260926
PY=/usr/local/share/pynq-venv/bin/python3
export XILINX_XRT=/usr
export TMPDIR=/dev/shm
export PATH="/usr/local/share/pynq-venv/bin:$PATH"
export PYTHONDONTWRITEBYTECODE=1
test "$(id -u)" -eq 0
sudo -n true
cd "$ROOT"
sha256sum -c PACKAGE_SHA256SUMS.txt
# The unchanged release assets were checked in M334; this gate checks only the
# new candidate package plus the mandatory same-terminal board environment.
"$PY" "$RELEASE/deployment/mage_vl4b/m175_m120_fixed_text_candidate/runtime/m120_board_env_preflight.py" \
  --candidate "$RELEASE/deployment/mage_vl4b/m175_m120_fixed_text_candidate" \
  --expected-package-manifest-sha256 406dcca340e4604baeb761445795391c43ec26bd99fa06ffae893d597b17414f \
  --result /dev/shm/m335_board_env_preflight.json
"$PY" "$ROOT/m335_board_gate.py"
