#!/usr/bin/env bash
set -euo pipefail

if [[ $# -ne 7 ]]; then
  echo "usage: $0 CANDIDATE LANGUAGE_ROOT HEAD_ROOT RESULT_DIR EXPECTED_PACKAGE_MANIFEST_SHA256 LAYER0_ACCEPTANCE EXPECTED_LAYER0_SHA256" >&2
  exit 2
fi

candidate=$1
language_root=$2
head_root=$3
result_dir=$4
expected_manifest=$5
layer0_acceptance=$6
expected_layer0_sha=$7

export XILINX_XRT=/usr
export TMPDIR=/dev/shm
export PATH=/usr/local/share/pynq-venv/bin:/usr/local/bin:/usr/bin:/bin
export PYTHONDONTWRITEBYTECODE=1
mkdir -p "$result_dir"

python3 "$candidate/runtime/m120_board_env_preflight.py" \
  --candidate "$candidate" \
  --expected-package-manifest-sha256 "$expected_manifest" \
  --result "$result_dir/fixed_text_environment.json"

python3 "$candidate/runtime/m160_verify_m120_layer0_predecessor.py" \
  --layer0-acceptance "$layer0_acceptance" \
  --expected-sha256 "$expected_layer0_sha"

python3 "$candidate/runtime/text_e2e_gate.py" \
  --overlay "$candidate/overlay/m120_m89x2_t32.bit" \
  --language "$language_root" \
  --head "$head_root" \
  --language-contract "$candidate/contracts/M126_LANGUAGE_RUNTIME_CONTRACT_RESULT.json" \
  --head-contract "$candidate/contracts/M126_LMHEAD_RUNTIME_CONTRACT_RESULT.json" \
  --auxiliary "$candidate/auxiliary/m77_text_aux_fp16.npz" \
  --auxiliary-manifest "$candidate/auxiliary/M77_TEXT_AUX_MANIFEST.json" \
  --reference "$candidate/auxiliary/official_cpu_text_1token.json" \
  --result "$result_dir/fixed_text_measurement.json" \
  --weight-mode staged-low-cma

echo M160_M120_FIXED_TEXT_E2E_RUNNER_PASS
