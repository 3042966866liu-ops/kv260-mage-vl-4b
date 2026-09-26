#!/usr/bin/env bash
set -euo pipefail

candidate=/home/ubuntu/tellme_m120_m89x2_20260901/m120_text4b_board_candidate
cpu_root=/home/ubuntu/tellme_m330_native_cpu_20260926
root=/home/ubuntu/tellme_m331_paired_20260926
result_dir="$root/results"
script="$root/m331_paired_native_pl.py"
script_sha=dc12906c72abc491d0b390ebd8cb9f76fae780810a442f1711c6c76f4f340f22
cpu_binary_sha=97730113c0c34c99c9b61aaf5ad70ac57c00a6749c89752ea2b510c338f36354
manifest_sha=7600ba1af87680fe1294ae6dc88f8e0968f23b2e38ca48dbfd316e351ea76e3e

[[ $(id -u) -eq 0 ]] || { echo M331_ROOT_REQUIRED >&2; exit 1; }
sudo -n true || { echo M331_SUDO_EXPIRED >&2; exit 1; }
[[ -f "$script" && -d "$candidate" ]] || { echo M331_ASSET_MISSING >&2; exit 1; }
[[ ! -e "$result_dir/paired.json" ]] || { echo M331_REFUSE_RESULT_OVERWRITE >&2; exit 1; }
[[ $(sha256sum "$script" | cut -d' ' -f1) == "$script_sha" ]] || { echo M331_SCRIPT_HASH_FAIL >&2; exit 1; }
[[ $(sha256sum "$cpu_root/m330_native_fixture_cpu" | cut -d' ' -f1) == "$cpu_binary_sha" ]] || { echo M331_CPU_BINARY_HASH_FAIL >&2; exit 1; }
command -v fuser >/dev/null || { echo M331_FUSER_MISSING >&2; exit 1; }
if fuser -s /dev/dri/card1 /dev/dri/renderD128; then
  echo M331_FPGA_DEVICE_ALREADY_OWNED >&2
  exit 1
fi
if [[ -n $(ss -H -ltn sport = :8001) ]]; then
  echo M331_STABLE_WEB_SERVICE_ACTIVE >&2
  exit 1
fi

mkdir -p "$result_dir"
export XILINX_XRT=/usr TMPDIR=/dev/shm PYTHONDONTWRITEBYTECODE=1
export PATH=/usr/local/share/pynq-venv/bin:/usr/local/bin:/usr/bin:/bin
export OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1
python3 "$candidate/runtime/m120_board_env_preflight.py" \
  --candidate "$candidate" --expected-package-manifest-sha256 "$manifest_sha" \
  --result "$result_dir/environment.json"

set +e
python3 "$script" --candidate "$candidate" --cpu-root "$cpu_root" \
  --pairs 10 --result "$result_dir/paired.json"
gate_rc=$?
set -e
if (( gate_rc != 0 )); then
  echo "M331_PAIR_GATE_FAIL rc=$gate_rc result=$result_dir/paired.json" >&2
  exit "$gate_rc"
fi
echo "M331_PAIR_GATE_PASS result=$result_dir/paired.json"
