#!/usr/bin/env python3
"""Build a clean four-member M163 COM3 bootstrap."""

from __future__ import annotations

import hashlib
import json
import os
import shutil
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "tmp/m163_network/m163_bootstrap"
RESULT = ROOT / "deployment/mage_vl4b/M163_M120_PUSH_BOOTSTRAP_RESULT.json"
M140 = ROOT / "deployment/mage_vl4b/M140_M120_SINGLE_CHAIN_BOARD_RESULT_01.json"
EXPECTED_M140_SHA = "60bc5dad7f3609c32b4698ebbb372eba9a3ab9e74b273969dd322299b4431cbb"


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> int:
    if sha256(M140) != EXPECTED_M140_SHA:
        raise RuntimeError("M163 exact M140 identity mismatch")
    if OUTPUT.exists() or OUTPUT.with_name(OUTPUT.name + ".partial").exists():
        raise RuntimeError("M163 clean bootstrap output required")
    staging = OUTPUT.with_name(OUTPUT.name + ".partial")
    staging.mkdir(parents=True)
    sources = {
        "m163_m120_board_push_receiver.py": ROOT / "scripts/m163_m120_board_push_receiver.py",
        "m163_run_m120_push_receiver.sh": ROOT / "scripts/m163_run_m120_push_receiver.sh",
        "m163_verify_push_bootstrap.py": ROOT / "scripts/m163_verify_push_bootstrap.py",
        "M140_M120_SINGLE_CHAIN_BOARD_RESULT_01.json": M140,
    }
    entries = []
    for relative, source in sources.items():
        target = staging / relative
        shutil.copyfile(source, target)
        entries.append({"path": relative, "bytes": target.stat().st_size, "sha256": sha256(target)})
    manifest = {
        "date": "2026-09-01",
        "gate": "M163-M120-PC-push-bootstrap",
        "status": "PASS",
        "candidate_build_id": "0x4D395832",
        "m140_result_sha256": EXPECTED_M140_SHA,
        "temporary_board_ip": "192.168.0.2/24",
        "pc_source_ip": "192.168.0.10",
        "listen_port": 8766,
        "files": entries,
        "file_count": len(entries),
    }
    (staging / "PACKAGE_MANIFEST.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    os.replace(staging, OUTPUT)
    result = {
        "date": "2026-09-01",
        "gate": "M163-M120-PC-push-bootstrap-build",
        "status": "PASS",
        "classification": "Clean outbound-PC network bootstrap only; no COM3 upload, IP change, weight transfer or FPGA execution.",
        "directory": OUTPUT.relative_to(ROOT).as_posix(),
        "package_manifest_sha256": sha256(OUTPUT / "PACKAGE_MANIFEST.json"),
        "file_count": 4,
        "total_bytes": sum(item["bytes"] for item in entries),
        "windows_inbound_firewall_rule_required": False,
        "board_state_changed": False,
    }
    RESULT.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, indent=2))
    print("M163_PUSH_BOOTSTRAP_BUILD_PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
