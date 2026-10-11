#!/usr/bin/env python3
"""Create hash-locked M89-X full-shell evidence after Vivado gates pass."""

from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PACKAGE = ROOT / "deployment/mage_vl4b/m89x_board_candidate"
REPORTS = PACKAGE / "full_shell_reports"
RESULT = ROOT / "deployment/mage_vl4b/M89X_FULL_SHELL_IMPLEMENTATION_RESULT.json"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(8 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def require(path: Path) -> Path:
    if not path.is_file() or path.stat().st_size == 0:
        raise RuntimeError(f"required implementation artifact missing: {path}")
    return path


def summary() -> dict[str, str]:
    values: dict[str, str] = {}
    for line in require(REPORTS / "gate_summary.txt").read_text(encoding="utf-8").splitlines():
        key, value = line.split("=", 1)
        values[key] = value
    if values.get("status") != "PASS_FULL_KV260_SHELL_IMPLEMENTATION":
        raise RuntimeError("Vivado implementation summary is not passing")
    if float(values["wns_ns"]) < 0 or float(values["whs_ns"]) < 0:
        raise RuntimeError("implementation timing is not passing")
    if int(values["serious_drc_count"]) != 0:
        raise RuntimeError("implementation DRC is not passing")
    return values


def utilization() -> dict[str, dict[str, float | int]]:
    text = require(REPORTS / "impl_utilization.rpt").read_text(encoding="utf-8", errors="replace")
    labels = ("CLB LUTs", "CLB Registers", "Block RAM Tile", "URAM", "DSPs")
    output: dict[str, dict[str, float | int]] = {}
    for label in labels:
        match = re.search(rf"^\|\s*{re.escape(label)}\s*\|\s*([0-9.]+)\s*\|.*?\|\s*([0-9.]+)\s*\|\s*([0-9.]+)\s*\|$", text, re.MULTILINE)
        if not match:
            raise RuntimeError(f"utilization row missing: {label}")
        used = float(match.group(1))
        available = float(match.group(2))
        output[label] = {
            "used": int(used) if used.is_integer() else used,
            "available": int(available) if available.is_integer() else available,
            "percent": float(match.group(3)),
        }
    return output


def main() -> int:
    gate = summary()
    required_files = [
        PACKAGE / "overlay/m89x_t32.bit",
        PACKAGE / "overlay/m89x_t32.hwh",
        PACKAGE / "overlay/mage_m89x_t32_highddr.xsa",
        REPORTS / "impl_utilization.rpt",
        REPORTS / "impl_utilization_hierarchical.rpt",
        REPORTS / "impl_timing_summary.rpt",
        REPORTS / "impl_drc.rpt",
        REPORTS / "impl_route_status.rpt",
        REPORTS / "address_audit.txt",
        REPORTS / "gate_summary.txt",
    ]
    files = []
    for path in required_files:
        require(path)
        files.append({
            "path": path.relative_to(ROOT).as_posix(),
            "bytes": path.stat().st_size,
            "sha256": sha256(path),
        })
    result = {
        "date": "2026-08-31",
        "build": "M89-X1/Z2",
        "build_id": gate["build_id"],
        "status": gate["status"],
        "marker": "M89X_FULL_KV260_SHELL_IMPLEMENTATION_PASS",
        "timing": {"wns_ns": float(gate["wns_ns"]), "whs_ns": float(gate["whs_ns"])},
        "serious_drc_count": int(gate["serious_drc_count"]),
        "utilization": utilization(),
        "axi_lite_config_register": gate["config_register"],
        "control_address_width": 8,
        "deployed": False,
        "board_state_changed": False,
        "stable_rollback_preserved": True,
        "files": files,
        "boundary": "Full KV260 Linux/AXI/DMA shell implementation evidence; not board correctness or performance evidence.",
        "next_gate": "Package the fixed-reference Linux board candidate without loading it onto the board.",
    }
    RESULT.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(result["marker"])
    print(json.dumps({"wns_ns": result["timing"]["wns_ns"], "whs_ns": result["timing"]["whs_ns"], "deployed": False}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
