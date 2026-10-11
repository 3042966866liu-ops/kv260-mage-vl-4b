#!/usr/bin/env bash
set -euo pipefail
candidate=/home/ubuntu/tellme_m89x1_qkv_20260831/m89x_board_candidate
result=/home/ubuntu/tellme_m89x1_qkv_20260831/result
runtime="$candidate/runtime"
expected_gate=48798dabf11433c6cc1d437c89cc4432206b8700db9f9e3f6c962198ee6e155a
export PATH=/usr/local/share/pynq-venv/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin
export TMPDIR=/dev/shm
export XILINX_XRT=/usr
sudo -n true
test "$(sha256sum "$runtime/m89x1_qkv_hash_gate.py" | awk '{print $1}')" = "$expected_gate"
/usr/local/share/pynq-venv/bin/python3 "$runtime/board_env_preflight.py" --candidate "$candidate" --expected-package-manifest-sha256 c4645fdf2ff1b299d3a7fb302fed72a8d50a95b658ad76e464c67a72a1a6cf50 --result "$result/M89X1_QKV_ENV_PREFLIGHT_RESULT.json"
timeout 45s /usr/local/share/pynq-venv/bin/python3 "$runtime/m89x1_qkv_hash_gate.py" --candidate "$candidate" --result "$result/M89X1_QKV_BOARD_RESULT.json"
echo M89X1_QKV_HASH_GATE_RUNNER_PASS
