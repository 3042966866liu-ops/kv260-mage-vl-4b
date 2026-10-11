#!/bin/bash
set -euo pipefail
export PYTHONDONTWRITEBYTECODE=1
cd /home/ubuntu/m338_import_probe_01
printf '%s\n' '3c9744374b2c5ade1ce809840fcaad90d75938bbee64c2bf7eb7d5c4b572f07b  m338_real_import_probe.py' | sha256sum -c -
/usr/local/share/pynq-venv/bin/python3 -B /home/ubuntu/m338_import_probe_01/m338_real_import_probe.py
