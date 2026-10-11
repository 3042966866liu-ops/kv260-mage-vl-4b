#!/usr/bin/env bash
set -euo pipefail
[[ $EUID == 0 && $# == 1 ]] || exit 65
task_dir=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)
exec /usr/local/share/pynq-venv/bin/python -B "$task_dir/m400_owner_recovery_driver.py" --enable-controlled-owner-recovery "$1"
