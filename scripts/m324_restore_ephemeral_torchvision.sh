#!/usr/bin/env bash
set -euo pipefail

root=/home/ubuntu/tellme_m120_m89x2_20260901
wheel=$root/m249_ssdlite_board_candidate/wheels/torchvision-0.27.1+cpu-cp310-cp310-manylinux_2_28_aarch64.whl
site=/dev/shm/tellme_m254_torchvision
runtime=$root/m190_mage_runtime
expected=3323edb900ca46d29dba267ee809e55fe5fe09cd3d9f54124a7c5ed33a6a2dbe
python=/usr/local/share/pynq-venv/bin/python

[[ $(id -u) -eq 0 ]] || { echo M324_ROOT_REQUIRED >&2; exit 1; }
[[ -f $wheel ]] || { echo M324_WHEEL_MISSING >&2; exit 1; }
[[ -d $runtime/torch ]] || { echo M324_ISOLATED_TORCH_MISSING >&2; exit 1; }
actual=$(sha256sum "$wheel")
[[ ${actual%% *} == "$expected" ]] || { echo M324_WHEEL_HASH_MISMATCH >&2; exit 1; }
[[ ! -L $site ]] || { echo M324_REFUSE_SYMLINK >&2; exit 1; }
export PYTHONDONTWRITEBYTECODE=1

if [[ ! -e $site ]]; then
  stage=$(mktemp -d /dev/shm/tellme_m324_torchvision.XXXXXXXX)
  "$python" -B -m pip install --no-deps --no-index --target "$stage" "$wheel"
  PYTHONPATH="$stage:$runtime" "$python" -B -c 'import torch,torchvision; from torchvision.ops import nms; assert torch.__version__ == "2.12.1+cpu" and torchvision.__version__ == "0.27.1+cpu"; assert nms(torch.tensor([[0.,0.,2.,2.]]),torch.tensor([.9]),.5).numel() == 1'
  [[ ! -e $site ]] || { echo M324_TARGET_APPEARED_CONCURRENTLY >&2; exit 1; }
  mv -T -- "$stage" "$site"
fi

[[ -d $site/torchvision ]] || { echo M324_SITE_INCOMPLETE >&2; exit 1; }
PYTHONPATH="$site:$runtime" "$python" -B -c 'import torch,torchvision; from torchvision.ops import nms; assert torch.__version__ == "2.12.1+cpu" and torchvision.__version__ == "0.27.1+cpu"; assert nms(torch.tensor([[0.,0.,2.,2.]]),torch.tensor([.9]),.5).numel() == 1'
echo M324_EPHEMERAL_TORCHVISION_RESTORED_PASS
