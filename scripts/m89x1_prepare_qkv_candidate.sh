#!/usr/bin/env bash
set -euo pipefail

source=/home/ubuntu/tellme_m89x1_waitfix_20260831/m89x_board_candidate
target=/home/ubuntu/tellme_m89x1_qkv_20260831/m89x_board_candidate

test -d "$source"
test ! -e "$target"
mkdir -p "$(dirname "$target")"
cp -a "$source" "$target"
echo M89X1_QKV_CANDIDATE_PREPARE_PASS
