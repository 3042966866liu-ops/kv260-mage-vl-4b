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
language=/home/ubuntu/tellme_m89x_upload/m89y_language_fourport
head=/home/ubuntu/tellme_m89x_upload/m89z2_lmhead_w4_fourport

export PATH=/usr/local/share/pynq-venv/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin
export TMPDIR=/dev/shm
export XILINX_XRT=/usr
export PYTHONDONTWRITEBYTECODE=1

sudo -n true
mkdir -p "$result_dir"
environment="$result_dir/M89X1_HS64_FIXED_TEXT_ENV_PREFLIGHT.json"
measurement="$result_dir/M89X1_HS64_FIXED_TEXT_E2E_MEASUREMENT.json"
formal="$result_dir/M89X1_HS64_FIXED_TEXT_E2E_GATE_RESULT.json"

/usr/local/share/pynq-venv/bin/python3 "$runtime/board_env_preflight.py" \
  --candidate "$candidate" \
  --expected-package-manifest-sha256 "$expected_manifest" \
  --result "$environment"

set +e
timeout 1200s /usr/local/share/pynq-venv/bin/python3 "$runtime/text_e2e_gate.py" \
  --overlay "$candidate/overlay/m89x_t32.bit" \
  --language "$language" \
  --head "$head" \
  --language-contract "$candidate/contracts/M89X_MERGED_RUNTIME_CONTRACT_RESULT.json" \
  --head-contract "$candidate/contracts/M89Z2_LMHEAD_RUNTIME_CONTRACT_RESULT.json" \
  --auxiliary "$candidate/auxiliary/m77_text_aux_fp16.npz" \
  --auxiliary-manifest "$candidate/auxiliary/M77_TEXT_AUX_MANIFEST.json" \
  --reference "$candidate/auxiliary/official_cpu_text_1token.json" \
  --weight-mode staged-low-cma \
  --result "$measurement"
measurement_rc=$?
set -e
if [[ $measurement_rc -ne 0 ]]; then
  echo "M89X1_HS64_FIXED_TEXT_E2E_MEASUREMENT_FAIL rc=$measurement_rc" >&2
  exit "$measurement_rc"
fi

/usr/local/share/pynq-venv/bin/python3 "$runtime/m89x1_fixed_text_acceptance_gate.py" \
  --environment "$environment" \
  --measurement "$measurement" \
  --result "$formal" \
  --expected-package-manifest-sha256 "$expected_manifest"
echo M89X1_HS64_FIXED_TEXT_E2E_GATE_RUNNER_PASS
