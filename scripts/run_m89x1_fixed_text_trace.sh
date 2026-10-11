#!/usr/bin/env bash
set -euo pipefail

if [[ $# -ne 3 ]]; then
  echo "usage: $0 CANDIDATE RESULT_DIR EXPECTED_PACKAGE_MANIFEST_SHA256" >&2
  exit 64
fi
candidate="$1"
result_dir="$2"
expected_manifest="$3"
runtime="$candidate/runtime"
export PATH=/usr/local/share/pynq-venv/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin
export TMPDIR=/dev/shm
export XILINX_XRT=/usr
export PYTHONDONTWRITEBYTECODE=1
sudo -n true
mkdir -p "$result_dir"
/usr/local/share/pynq-venv/bin/python3 "$runtime/board_env_preflight.py" \
  --candidate "$candidate" \
  --expected-package-manifest-sha256 "$expected_manifest" \
  --result "$result_dir/M89X1_HS64_FIXED_TEXT_TRACE_ENV.json"
timeout 300s /usr/local/share/pynq-venv/bin/python3 \
  "$runtime/m89x1_fixed_text_e2e_trace.py" \
  --candidate "$candidate" \
  --expected-package-manifest-sha256 "$expected_manifest" \
  --result "$result_dir/M89X1_HS64_FIXED_TEXT_TRACE_RESULT.json"
echo M89X1_HS64_FIXED_TEXT_TRACE_RUNNER_PASS
