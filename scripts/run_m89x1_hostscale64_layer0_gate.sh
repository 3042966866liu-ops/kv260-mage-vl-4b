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

sudo -n true
mkdir -p "$result_dir"
/usr/local/share/pynq-venv/bin/python3 "$runtime/board_env_preflight.py" \
  --candidate "$candidate" \
  --expected-package-manifest-sha256 "$expected_manifest" \
  --result "$result_dir/M89X1_HS64_LAYER0_ENV_PREFLIGHT.json"

measurement="$result_dir/M89X1_HS64_LAYER0_MEASUREMENT.json"
formal="$result_dir/M89X1_HS64_LAYER0_GATE_RESULT.json"
set +e
timeout 480s /usr/local/share/pynq-venv/bin/python3 \
  "$runtime/m89x1_layer0_tolerance_diagnostic.py" \
  --candidate "$candidate" \
  --expected-package-manifest-sha256 "$expected_manifest" \
  --result "$measurement"
measurement_rc=$?
set -e
if [[ $measurement_rc -ne 0 ]]; then
  echo "M89X1_HS64_LAYER0_MEASUREMENT_FAIL rc=$measurement_rc" >&2
  exit "$measurement_rc"
fi

/usr/local/share/pynq-venv/bin/python3 "$runtime/m89x1_layer0_acceptance_gate.py" \
  --measurement "$measurement" --result "$formal"
echo M89X1_HS64_LAYER0_GATE_RUNNER_PASS
