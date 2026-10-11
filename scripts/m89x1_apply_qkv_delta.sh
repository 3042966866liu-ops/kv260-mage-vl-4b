#!/usr/bin/env bash
set -euo pipefail

archive=/home/ubuntu/m89x1_qkv_delta.tar
target=/home/ubuntu/tellme_m89x1_qkv_20260831/m89x_board_candidate
archive_sha256=c801d8df9ba1f32b896ebd0845989b6bedf5e8f464a383d99988d6dc36e70e24
manifest_sha256=2ecdc09bc0ef8124c653976fc84064ce929d9e67793cc619dc456466a427977c

test -d "$target"
test "$(sha256sum "$archive" | awk '{print $1}')" = "$archive_sha256"
expected=$'README.md\nPACKAGE_MANIFEST.json\nruntime/single_chain_smoke.py\nruntime/single_chain_reference.py\nruntime/run_m89x1_single_chain_gate.sh\nreference/layer0_qkv_reference.json'
actual="$(tar -tf "$archive" | tr -d '\r')"
test "$actual" = "$expected"
tar -xf "$archive" -C "$target"
test "$(sha256sum "$target/PACKAGE_MANIFEST.json" | awk '{print $1}')" = "$manifest_sha256"
echo M89X1_QKV_DELTA_APPLY_PASS
