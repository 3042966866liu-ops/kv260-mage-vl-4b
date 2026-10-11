#!/usr/bin/env bash
set -uo pipefail

ROOT=/home/ubuntu/tellme_m89x_upload/m89x_board_candidate
SCRIPT=/home/ubuntu/tellme_m89x_upload/m89x_minimal_kernel_board_smoke.py
OUT=/home/ubuntu/tellme_m89x_upload/M89X_MINIMAL_KERNEL_BOARD_RESULT.json
EXPECTED_BOOT=7319e263ee10d7914e1769d635c204611d5627f72ef5193d7530c65882c11b7d
EXPECTED_PACKAGE=4d2b0d7c84e9f2a79e66494ea321a14c6b1ed1a457e99895aade9f300b174b59
EXPECTED_SCRIPT=a4825517748b5fc7ed076db79c52ad861df79dd9ba21a8bf3cdd8758372c1f99
PYTHON=/usr/local/share/pynq-venv/bin/python3

fail() {
    echo "M89X_MINIMAL_PREFLIGHT_FAIL reason=$1" >&2
    exit 90
}

[[ "$(uname -m)" == aarch64 ]] || fail arch
grep -qw cma=800M /proc/cmdline || fail cma
[[ ! -e /boot/firmware/user-override.dtb ]] || fail active_dtb
[[ "$(sha256sum /boot/firmware/boot.scr.uimg | awk '{print $1}')" == "$EXPECTED_BOOT" ]] || fail boot_hash
[[ "$(sha256sum "$ROOT/PACKAGE_MANIFEST.json" | awk '{print $1}')" == "$EXPECTED_PACKAGE" ]] || fail package_hash
[[ "$(sha256sum "$SCRIPT" | awk '{print $1}')" == "$EXPECTED_SCRIPT" ]] || fail script_hash
[[ -x "$PYTHON" ]] || fail pynq_python
[[ -f "$ROOT/overlay/m89x_t32.bit" && -f "$ROOT/overlay/m89x_t32.hwh" ]] || fail overlay

rm -f "$OUT"
echo M89X_MINIMAL_PREFLIGHT_PASS
echo PRE_CMA
grep -E 'CmaTotal|CmaFree' /proc/meminfo

set +e
env \
    PATH=/usr/local/share/pynq-venv/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin \
    PYTHONPATH=/usr/local/share/pynq-venv/lib/python3.10/site-packages \
    XILINX_XRT=/usr \
    LD_LIBRARY_PATH=/usr/lib \
    "$PYTHON" "$SCRIPT" --candidate "$ROOT" --result "$OUT"
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
if result.get("status") != "PASS" or result.get("build_id") != "0x4d383958":
    raise SystemExit("minimal result identity gate failed")
print("M89X_MINIMAL_RESULT_JSON_PASS")
PY
echo M89X_MINIMAL_KERNEL_BOARD_SMOKE_WRAPPER_PASS
