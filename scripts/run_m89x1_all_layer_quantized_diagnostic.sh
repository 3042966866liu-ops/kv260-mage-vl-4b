#!/usr/bin/env bash
set -euo pipefail

if [[ $# -ne 4 ]]; then
  echo "usage: $0 CANDIDATE RESULT_DIR EXPECTED_PACKAGE_MANIFEST_SHA256 EXPECTED_GOLDEN_SHA256" >&2
  exit 64
fi

candidate="$1"
result_dir="$2"
expected_manifest="$3"
expected_golden="$4"
runtime="$candidate/runtime"

export PATH=/usr/local/share/pynq-venv/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin
export TMPDIR=/dev/shm
export XILINX_XRT=/usr
export PYTHONDONTWRITEBYTECODE=1

sudo -n true
mkdir -p "$result_dir"
environment="$result_dir/M89X1_ALL_LAYER_QUANTIZED_ENV.json"
measurement="$result_dir/M89X1_ALL_LAYER_QUANTIZED_DIAGNOSTIC.json"

/usr/local/share/pynq-venv/bin/python3 "$runtime/board_env_preflight.py" \
  --candidate "$candidate" \
  --expected-package-manifest-sha256 "$expected_manifest" \
  --result "$environment"

set +e
timeout 1200s /usr/local/share/pynq-venv/bin/python3 \
  "$runtime/m89x1_all_layer_quantized_board_diagnostic.py" \
  --candidate "$candidate" \
  --expected-package-manifest-sha256 "$expected_manifest" \
  --golden-sketch "$candidate/auxiliary/m89x1_quantized_cpu_family_sketch.json" \
  --expected-golden-sketch-sha256 "$expected_golden" \
  --quantized-reference "$candidate/contracts/M89X1_QUANTIZED_CPU_ALL_LAYER_REFERENCE_RESULT.json" \
  --result "$measurement"
gate_rc=$?
set -e

if [[ $gate_rc -ne 0 ]]; then
  echo "M89X1_ALL_LAYER_QUANTIZED_DIAGNOSTIC_FAIL rc=$gate_rc" >&2
  exit "$gate_rc"
fi
echo M89X1_ALL_LAYER_QUANTIZED_DIAGNOSTIC_RUNNER_MEASURED
