#!/usr/bin/env python3
"""Static fail-closed audit for the one-command authorized M20 cycle."""

from __future__ import annotations

import hashlib
import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / "deployment/qwen25_3b_directddr_chain"
ARM = BASE / "arm_reserved1664_m20_authorized_cycle.sh"
RUNNER = BASE / "run_reserved1664_m20_authorized_cycle.sh"
UNIT = BASE / "tellme-reserved1664-m20-cycle.service"
CLEANUP = BASE / "run_reserved1664_m20_authorized_cleanup.sh"
CLEANUP_UNIT = BASE / "tellme-reserved1664-m20-cleanup.service"


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def assigned(source: str, name: str) -> str:
    match = re.search(rf"^{re.escape(name)}=([0-9a-f]{{64}})$", source, re.MULTILINE)
    if not match:
        raise AssertionError(f"missing locked {name}")
    return match.group(1)


def main() -> int:
    arm = ARM.read_text()
    runner = RUNNER.read_text()
    unit = UNIT.read_text()
    cleanup = CLEANUP.read_text()
    cleanup_unit = CLEANUP_UNIT.read_text()
    assert "__RUNNER_SHA__" not in arm and "__UNIT_SHA__" not in arm
    assert assigned(arm, "INSTALLER_SHA") == sha256(BASE / "install_reserved1664_m20_boot.sh")
    assert assigned(arm, "ROLLBACK_SHA") == sha256(BASE / "rollback_reserved1664_boot.sh")
    assert assigned(arm, "RUNNER_SHA") == sha256(RUNNER)
    assert assigned(arm, "UNIT_SHA") == sha256(UNIT)
    assert assigned(arm, "CLEANUP_RUNNER_SHA") == sha256(CLEANUP)
    assert assigned(arm, "CLEANUP_UNIT_SHA") == sha256(CLEANUP_UNIT)
    assert assigned(runner, "PREPARE_SHA") == sha256(BASE / "prepare_reserved1664_m20_full_gate.sh")
    assert assigned(runner, "FULL_GATE_SHA") == sha256(BASE / "run_reserved1664_m20_full_gate.sh")
    assert assigned(runner, "ROLLBACK_SHA") == sha256(BASE / "rollback_reserved1664_boot.sh")
    enable = "systemctl enable tellme-reserved1664-m20-cycle.service tellme-reserved1664-m20-cleanup.service"
    assert arm.index('bash "$INSTALLER" --check-only') < arm.index(enable)
    assert arm.index(enable) < arm.rindex('bash "$INSTALLER"')
    assert runner.index('bash "$ROLLBACK"') < runner.index("systemd-run --unit=tellme-reserved1664-m20-stable-reboot")
    assert "--on-active=120s" in runner
    assert "systemctl daemon-reload" not in runner
    assert "systemctl disable tellme-reserved1664-m20-cycle.service" not in runner
    assert "timeout --signal=TERM --kill-after=60s" in runner
    assert "RECOVERY_FAIL_NO_AUTOMATIC_REBOOT" in runner
    assert "QWEN_RESERVED1664_AUTHORIZED_ARM_FAILURE_ROLLBACK_PASS" in arm
    assert "QWEN_RESERVED1664_AUTHORIZED_ARM_FAILURE_RECOVERY_REQUIRED_SERVICE_LEFT_ARMED" in arm
    assert "ConditionPathExists=/boot/firmware/user-override.dtb" in unit
    assert "ExecStart=/usr/local/sbin/tellme-reserved1664-m20-cycle" in unit
    assert "ConditionPathExists=!/boot/firmware/user-override.dtb" in cleanup_unit
    assert "ExecStart=/usr/local/sbin/tellme-reserved1664-m20-cleanup" in cleanup_unit
    assert "systemctl daemon-reload" not in cleanup
    assert "QWEN_M20_RESERVED1664_AUTHORIZED_STABLE_CLEANUP_PASS" in cleanup
    print("QWEN_M20_RESERVED1664_AUTHORIZED_CYCLE_AUDIT_PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
