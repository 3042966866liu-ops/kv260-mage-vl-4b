#!/usr/bin/env bash
set -uo pipefail

ROOT=/home/ubuntu/tellme_m89x_upload/m89x_board_candidate
LANGUAGE=/home/ubuntu/tellme_m89x_upload/m89y_language_fourport
HEAD=/home/ubuntu/tellme_m89x_upload/m89z2_lmhead_w4_fourport
OUT=/home/ubuntu/tellme_m89x_upload/M89X_SINGLE_CHAIN_BOARD_RESULT.json
EXPECTED_BOOT=7319e263ee10d7914e1769d635c204611d5627f72ef5193d7530c65882c11b7d
EXPECTED_PACKAGE=4d2b0d7c84e9f2a79e66494ea321a14c6b1ed1a457e99895aade9f300b174b59
PYTHON=/usr/local/share/pynq-venv/bin/python3

fail() {
    echo "M89X_SINGLE_CHAIN_PREFLIGHT_FAIL reason=$1" >&2
    exit 90
}

[[ "$(uname -m)" == aarch64 ]] || fail arch
grep -qw cma=800M /proc/cmdline || fail cma
[[ ! -e /boot/firmware/user-override.dtb ]] || fail active_dtb
[[ "$(sha256sum /boot/firmware/boot.scr.uimg | awk '{print $1}')" == "$EXPECTED_BOOT" ]] || fail boot_hash
[[ "$(sha256sum "$ROOT/PACKAGE_MANIFEST.json" | awk '{print $1}')" == "$EXPECTED_PACKAGE" ]] || fail package_hash
[[ -x "$PYTHON" ]] || fail pynq_python
[[ -f "$ROOT/overlay/m89x_t32.bit" && -f "$ROOT/overlay/m89x_t32.hwh" ]] || fail overlay
[[ -f "$ROOT/runtime/single_chain_smoke.py" ]] || fail diagnostic_runtime
[[ -f "$LANGUAGE/SIXPORT_LAYOUT_MANIFEST.json" ]] || fail language_layout
[[ -f "$HEAD/SIXPORT_LAYOUT_MANIFEST.json" ]] || fail head_layout

rm -f "$OUT"
echo M89X_SINGLE_CHAIN_PREFLIGHT_PASS
echo PRE_CMA
grep -E 'CmaTotal|CmaFree' /proc/meminfo

set +e
env \
    PATH=/usr/local/share/pynq-venv/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin \
    PYTHONPATH=/usr/local/share/pynq-venv/lib/python3.10/site-packages \
    XILINX_XRT=/usr \
    LD_LIBRARY_PATH=/usr/lib \
    "$PYTHON" "$ROOT/runtime/single_chain_smoke.py" \
        --overlay "$ROOT/overlay/m89x_t32.bit" \
        --language "$LANGUAGE" \
        --head "$HEAD" \
        --language-contract "$ROOT/contracts/M89X_MERGED_RUNTIME_CONTRACT_RESULT.json" \
        --head-contract "$ROOT/contracts/M89Z2_LMHEAD_RUNTIME_CONTRACT_RESULT.json" \
        --weight-mode staged-low-cma \
        --result "$OUT"
gate_rc=$?
set -e

echo POST_STATE
cat /sys/class/fpga_manager/fpga0/state
grep -E 'CmaTotal|CmaFree' /proc/meminfo
[[ -f "$OUT" ]] || fail missing_result
cat "$OUT"
[[ $gate_rc -eq 0 ]] || exit "$gate_rc"
"$PYTHON" - "$OUT" <<'PY'
import json
import sys
result = json.load(open(sys.argv[1], encoding="utf-8"))
if result.get("status") != "PASS":
    raise SystemExit("single-chain result JSON is not PASS")
evidence = result.get("evidence", {})
if evidence.get("build_id") != "0x4d383958":
    raise SystemExit("single-chain Build ID mismatch")
if evidence.get("host_calls") != 1:
    raise SystemExit("single-chain host call mismatch")
print("M89X_SINGLE_CHAIN_RESULT_JSON_PASS")
PY
echo M89X_SINGLE_CHAIN_BOARD_SMOKE_WRAPPER_PASS
