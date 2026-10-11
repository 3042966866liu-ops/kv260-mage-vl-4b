#!/usr/bin/env bash
set -euo pipefail

root=/home/ubuntu/tellme_qwen25_3b/packetdf_candidate

read_meminfo() {
  awk '/^(MemAvailable|Cached|SReclaimable|CmaTotal|CmaFree):/ { print }' /proc/meminfo
}

echo M17_HASH_CMA_BEFORE
read_meminfo
sha256sum \
  "$root/model/qwen25_3b_aux_fp16.bin" \
  "$root/model/qwen25_3b_linears_w4g64.mgs" \
  "$root/lm_head/qwen25_3b_lm_head_w4g64.mgs"
echo M17_HASH_CMA_AFTER
read_meminfo
