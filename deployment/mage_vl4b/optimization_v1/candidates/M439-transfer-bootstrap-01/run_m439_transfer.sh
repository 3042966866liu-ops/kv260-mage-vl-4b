#!/bin/bash
set -euo pipefail
[[ $EUID == 0 ]] || exit 65
[[ $# == 2 ]] || exit 64
task_here=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)
task_action=$1
task_manifest=$2
case "$task_action" in receive|collect) ;; *) exit 64;; esac
exec /usr/local/share/pynq-venv/bin/python -B "$task_here/m439_transfer.py" "$task_action" "$task_here" "$task_manifest"
