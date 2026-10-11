#!/usr/bin/env bash
set -euo pipefail
[[ $EUID == 0 && $# == 2 ]] || exit 65
task_dir=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)
export PYTHONDONTWRITEBYTECODE=1
exec /usr/local/share/pynq-venv/bin/python -B "$task_dir/m400_owner_readonly_probe.py" "$2" "$1"
