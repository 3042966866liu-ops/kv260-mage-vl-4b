#!/usr/bin/env bash
set -euo pipefail

if [[ $# -ne 6 ]]; then
  echo "usage: $0 CANDIDATE LANGUAGE_ROOT HEAD_ROOT RESULT_DIR EXPECTED_PACKAGE_MANIFEST_SHA256 EXPECTED_M143_RESULT_SHA256" >&2
  exit 2
fi

candidate=$1
language_root=$2
head_root=$3
result_dir=$4
expected_manifest=$5
expected_m143_result=$6

export XILINX_XRT=/usr
export TMPDIR=/dev/shm
export PATH=/usr/local/share/pynq-venv/bin:/usr/local/bin:/usr/bin:/bin
export PYTHONDONTWRITEBYTECODE=1
mkdir -p "$result_dir"

python3 "$candidate/runtime/m120_board_env_preflight.py" \
  --candidate "$candidate" \
  --expected-package-manifest-sha256 "$expected_manifest" \
  --result "$result_dir/environment.json"

observed_m143=$(sha256sum "$candidate/reference/M143_M120_LAYER0_BOUNDARY_FIXTURE_RESULT.json" | awk '{print $1}')
if [[ "$observed_m143" != "$expected_m143_result" ]]; then
  echo "M144_M143_RESULT_IDENTITY_FAIL expected=$expected_m143_result observed=$observed_m143" >&2
  exit 1
fi

python3 "$candidate/runtime/m120_layer0_boundary_diagnostic.py" \
  --overlay "$candidate/overlay/m120_m89x2_t32.bit" \
  --language "$language_root" \
  --head "$head_root" \
  --language-contract "$candidate/contracts/M126_LANGUAGE_RUNTIME_CONTRACT_RESULT.json" \
  --head-contract "$candidate/contracts/M126_LMHEAD_RUNTIME_CONTRACT_RESULT.json" \
  --auxiliary "$candidate/auxiliary/m77_text_aux_fp16.npz" \
  --auxiliary-manifest "$candidate/auxiliary/M77_TEXT_AUX_MANIFEST.json" \
  --reference "$candidate/auxiliary/official_cpu_text_1token.json" \
  --boundaries "$candidate/reference/m143_m120_layer0_boundaries.npz" \
  --boundaries-result "$candidate/reference/M143_M120_LAYER0_BOUNDARY_FIXTURE_RESULT.json" \
  --result "$result_dir/layer0_measurement.json" \
  --weight-mode staged-low-cma

python3 "$candidate/runtime/m120_layer0_boundary_acceptance.py" \
  --measurement "$result_dir/layer0_measurement.json" \
  --result "$result_dir/layer0_acceptance.json"

echo M144_M120_LAYER0_RUNNER_PASS
