#!/usr/bin/env bash
set -euo pipefail
candidate=/home/ubuntu/tellme_m89x1_qkv_20260831/m89x_board_candidate
result=/home/ubuntu/tellme_m89x1_qkv_20260831/result
runtime="$candidate/runtime"
expected_gate=691bb3b203e9e5965e61eef4f16ac58d96785279e4c07d27e613653457422f47
expected_helper=5c49e9a338aaa68d099902032def0248b8126e548dc7c95dc857b2f82c514c3e
export PATH=/usr/local/share/pynq-venv/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin
export TMPDIR=/dev/shm
export XILINX_XRT=/usr
sudo -n true
test "$(sha256sum "$runtime/m89x1_qkv_tolerance_diagnostic.py" | awk '{print $1}')" = "$expected_gate"
test "$(sha256sum "$runtime/m89x1_qkv_reference_helper.py" | awk '{print $1}')" = "$expected_helper"
/usr/local/share/pynq-venv/bin/python3 "$runtime/board_env_preflight.py" --candidate "$candidate" --expected-package-manifest-sha256 c4645fdf2ff1b299d3a7fb302fed72a8d50a95b658ad76e464c67a72a1a6cf50 --result "$result/M89X1_QKV_TOLERANCE_ENV_PREFLIGHT.json"
timeout 70s /usr/local/share/pynq-venv/bin/python3 "$runtime/m89x1_qkv_tolerance_diagnostic.py" --candidate "$candidate" --result "$result/M89X1_QKV_TOLERANCE_DIAGNOSTIC.json"
