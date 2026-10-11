#!/usr/bin/env python3
"""Prevent the reserved-DDR sync ioctl from colliding with Linux FIOASYNC."""

from __future__ import annotations

import ast
import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DRIVER = ROOT / "deployment/qwen25_3b_directddr_chain/reserved1664_mmap/tellme_reserved1664.c"
RUNTIME = ROOT / "deployment/qwen25_3b_directddr_chain/runtime/reserved_ddr_pool.py"


def python_sync_ioctl() -> int:
    tree = ast.parse(RUNTIME.read_text())
    for node in tree.body:
        if isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name) and target.id == "SYNC_IOCTL":
                    value = ast.literal_eval(node.value)
                    if not isinstance(value, int):
                        raise AssertionError("SYNC_IOCTL is not an integer")
                    return value
    raise AssertionError("SYNC_IOCTL assignment is missing")


def main() -> int:
    source = DRIVER.read_text()
    match = re.search(
        r"#define\s+TELLME_POOL_SYNC\s+_IO\(0x([0-9A-Fa-f]+),\s*0x([0-9A-Fa-f]+)\)",
        source,
    )
    assert match, "driver private ioctl definition is missing"
    driver_value = (int(match.group(1), 16) << 8) | int(match.group(2), 16)
    runtime_value = python_sync_ioctl()
    assert driver_value == runtime_value == 0xA701
    assert driver_value != 0x5452, "0x5452 is Linux FIOASYNC and is VFS-intercepted"
    assert "command != TELLME_POOL_SYNC" in source
    assert "wmb();" in source
    print("QWEN_RESERVED1664_IOCTL_PROTOCOL_UNIT_PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
