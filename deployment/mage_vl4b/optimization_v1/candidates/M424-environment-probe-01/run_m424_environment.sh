#!/bin/bash
set -euo pipefail
cd "$(dirname "$0")"
if [[ "${2:-}" == Collect ]]; then
  exec /usr/local/share/pynq-venv/bin/python -B m424_environment_probe.py "$1" Collect
fi
if [[ "${M424_ENABLE_READONLY_ENV:-0}" != 1 || "${2:-}" != Run ]]; then exit 2; fi
set +e
/usr/local/share/pynq-venv/bin/python -B m424_environment_probe.py "$1" --enable-readonly-probe
gate_rc=$?
set -e
printf 'M424_ENV_DONE gate_rc=%s\n' "$gate_rc"
exit "$gate_rc"
