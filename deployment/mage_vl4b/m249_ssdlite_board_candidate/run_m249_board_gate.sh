#!/usr/bin/env bash
set -euo pipefail

root=/home/ubuntu/tellme_m120_m89x2_20260901
candidate=$root/m249_ssdlite_board_candidate
runtime=$root/m190_mage_runtime
site=/dev/shm/tellme_m249_torchvision
result=$root/results/M249_KV260_SSDLITE_SPEED_RESULT.json

if [[ $(id -u) -ne 0 ]]; then
  echo M249_ROOT_REQUIRED >&2
  exit 1
fi
if [[ ! -d $runtime ]]; then
  echo M249_M190_RUNTIME_REQUIRED >&2
  exit 1
fi
rm -rf "$site"
mkdir -p "$site" "$root/results"
export PYTHONDONTWRITEBYTECODE=1
export TMPDIR=/dev/shm
export OMP_NUM_THREADS=4
export OPENBLAS_NUM_THREADS=4
export PYTHONPATH=$site:$runtime
/usr/local/share/pynq-venv/bin/python -m pip install --no-deps --no-index \
  --target "$site" "$candidate/wheels/torchvision-0.27.1+cpu-cp310-cp310-manylinux_2_28_aarch64.whl"
/usr/local/share/pynq-venv/bin/python "$candidate/runtime/m249_board_probe.py" \
  --candidate "$candidate" --result "$result" --threads 4
echo M249_KV260_SSDLITE_BOARD_GATE_RUNNER_PASS
