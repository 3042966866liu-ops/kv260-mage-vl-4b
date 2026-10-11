#!/usr/bin/env bash
set -euo pipefail

candidate=/home/ubuntu/tellme_m120_m89x2_20260901/m120_text4b_board_candidate
control=/home/ubuntu/tellme_m329_cpu_reference_20260926
result_dir="$control/results"
gate="$control/m329_pl_fixture_timing.py"
gate_sha=c8f607a00c600577086841878977120b7d4aa92c530f3bc44998a3ff48290235
stable_manifest_sha=7600ba1af87680fe1294ae6dc88f8e0968f23b2e38ca48dbfd316e351ea76e3e

[[ $(id -u) -eq 0 ]] || { echo M329_ROOT_REQUIRED >&2; exit 1; }
sudo -n true || { echo M329_SUDO_EXPIRED >&2; exit 1; }
[[ -f "$gate" && -d "$candidate" ]] || { echo M329_ASSET_MISSING >&2; exit 1; }
[[ ! -e "$result_dir/pl_fixture.json" ]] || { echo M329_REFUSE_RESULT_OVERWRITE >&2; exit 1; }
export XILINX_XRT=/usr TMPDIR=/dev/shm PYTHONDONTWRITEBYTECODE=1
export PATH=/usr/local/share/pynq-venv/bin:/usr/local/bin:/usr/bin:/bin
export OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=4
actual=$(sha256sum "$gate")
[[ ${actual%% *} == "$gate_sha" ]] || { echo M329_GATE_HASH_FAIL >&2; exit 1; }
command -v fuser >/dev/null || { echo M329_FUSER_MISSING >&2; exit 1; }
if fuser -s /dev/dri/card1 /dev/dri/renderD128; then
  echo M329_FPGA_DEVICE_ALREADY_OWNED >&2
  exit 1
fi
if [[ -n $(ss -H -ltn sport = :8001) ]]; then
  echo M329_STABLE_WEB_SERVICE_ACTIVE >&2
  exit 1
fi
mkdir -p "$result_dir"
python3 "$candidate/runtime/m120_board_env_preflight.py" \
  --candidate "$candidate" --expected-package-manifest-sha256 "$stable_manifest_sha" \
  --result "$result_dir/pl_environment.json"

set +e
python3 "$gate" --candidate "$candidate" --repeat 3 \
  --result "$result_dir/pl_fixture.json"
gate_rc=$?
set -e
if (( gate_rc != 0 )); then
  echo "M329_PL_FIXTURE_GATE_FAIL rc=$gate_rc result=$result_dir/pl_fixture.json" >&2
  exit "$gate_rc"
fi
echo "M329_PL_FIXTURE_GATE_PASS result=$result_dir/pl_fixture.json"
