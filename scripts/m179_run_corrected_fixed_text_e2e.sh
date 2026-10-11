#!/usr/bin/env bash
set -euo pipefail
[[ $# -eq 9 ]] || { echo 'M179 argument count mismatch' >&2; exit 2; }
candidate=$1; language=$2; head=$3; result=$4; manifest=$5; layer0=$6; layer0_sha=$7; verifier=$8; verifier_sha=$9
export XILINX_XRT=/usr TMPDIR=/dev/shm PYTHONDONTWRITEBYTECODE=1
export PATH=/usr/local/share/pynq-venv/bin:/usr/local/bin:/usr/bin:/bin
mkdir -p "$result"
python3 "$candidate/runtime/m120_board_env_preflight.py" --candidate "$candidate" --expected-package-manifest-sha256 "$manifest" --result "$result/environment.json"
python3 "$verifier" "$layer0" "$layer0_sha" "$verifier_sha"
python3 "$candidate/runtime/text_e2e_gate.py" \
  --overlay "$candidate/overlay/m120_m89x2_t32.bit" \
  --language "$language" --head "$head" \
  --language-contract "$candidate/contracts/M126_LANGUAGE_RUNTIME_CONTRACT_RESULT.json" \
  --head-contract "$candidate/contracts/M126_LMHEAD_RUNTIME_CONTRACT_RESULT.json" \
  --auxiliary "$candidate/auxiliary/m77_text_aux_fp16.npz" \
  --auxiliary-manifest "$candidate/auxiliary/M77_TEXT_AUX_MANIFEST.json" \
  --reference "$candidate/auxiliary/official_cpu_text_1token.json" \
  --result "$result/fixed_text_measurement.json" --weight-mode staged-low-cma
echo M179_M120_FIXED_TEXT_E2E_RUNNER_PASS
