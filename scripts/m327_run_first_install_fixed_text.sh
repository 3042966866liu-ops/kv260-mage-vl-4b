#!/usr/bin/env bash
set -euo pipefail

root=/home/ubuntu/tellme_release_install_20260926
control=/home/ubuntu/m327_backup_control
candidate="$root/deployment/mage_vl4b/m175_m120_fixed_text_candidate"
weights="$root/external_assets/weights"
result="$root/results/m327_first_install_fixed_text"
expected_install_manifest=fc69e69c0396e29e06d4852b06f680b2365cb31fdd1ffb036b0f85037b6f6d6e
expected_m175_manifest=406dcca340e4604baeb761445795391c43ec26bd99fa06ffae893d597b17414f

if [[ "$(id -u)" -ne 0 ]]; then echo 'M327_ROOT_REQUIRED' >&2; exit 2; fi
if ! sudo -n true; then echo 'M327_SAME_TERMINAL_SUDO_REQUIRED' >&2; exit 2; fi
if [[ ! -f "$root/INSTALL_BOARD_RESULT.json" ]]; then echo 'M327_INSTALL_RESULT_ABSENT' >&2; exit 2; fi
if [[ "$(sha256sum "$root/INSTALL_PACKAGE_MANIFEST.json" | awk '{print $1}')" != "$expected_install_manifest" ]]; then
  echo 'M327_INSTALL_MANIFEST_IDENTITY_FAIL' >&2; exit 2
fi
if ss -ltn '( sport = :8001 )' | grep -q ':8001'; then
  echo 'M327_STABLE_WEB_PORT_OCCUPIED' >&2; exit 2
fi

export XILINX_XRT=/usr
export TMPDIR=/dev/shm
export PATH=/usr/local/share/pynq-venv/bin:/usr/local/bin:/usr/bin:/bin
export PYTHONDONTWRITEBYTECODE=1
mkdir -p "$result"

python3 "$candidate/runtime/m120_board_env_preflight.py" \
  --candidate "$candidate" --expected-package-manifest-sha256 "$expected_m175_manifest" \
  --result "$result/env_build_id.json"
python3 "$control/m120_build_id_gate.py" --candidate "$candidate" \
  --result "$result/build_id.json"

# Historical single-descriptor, chain and layer gates are tied to this same
# bit/hwh SHA and remain in the package evidence. This runner does not promote
# a failed lower gate or claim they were freshly rerun in the new directory.
python3 "$candidate/runtime/m120_board_env_preflight.py" \
  --candidate "$candidate" --expected-package-manifest-sha256 "$expected_m175_manifest" \
  --result "$result/env_fixed_text.json"
python3 "$candidate/runtime/text_e2e_gate.py" \
  --overlay "$candidate/overlay/m120_m89x2_t32.bit" \
  --language "$weights/language_fourport" --head "$weights/lmhead_fourport" \
  --language-contract "$candidate/contracts/M126_LANGUAGE_RUNTIME_CONTRACT_RESULT.json" \
  --head-contract "$candidate/contracts/M126_LMHEAD_RUNTIME_CONTRACT_RESULT.json" \
  --auxiliary "$candidate/auxiliary/m77_text_aux_fp16.npz" \
  --auxiliary-manifest "$candidate/auxiliary/M77_TEXT_AUX_MANIFEST.json" \
  --reference "$candidate/auxiliary/official_cpu_text_1token.json" \
  --result "$result/fixed_text.json" --weight-mode staged-low-cma

echo M327_FIRST_INSTALL_FIXED_TEXT_PASS
