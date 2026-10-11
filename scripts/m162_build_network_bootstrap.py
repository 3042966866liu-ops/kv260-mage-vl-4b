#!/usr/bin/env python3
"""Build a clean four-file M162 network-control bootstrap."""

from __future__ import annotations

import hashlib
import json
import os
import shutil
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "tmp/m162_network/m162_bootstrap_v2"
RESULT = ROOT / "deployment/mage_vl4b/M162_M120_NETWORK_BOOTSTRAP_RESULT_V2.json"
SOURCES = {
    "m162_m120_network_board_import.py": ROOT / "scripts/m162_m120_network_board_import.py",
    "m162_run_m120_network_import.sh": ROOT / "scripts/m162_run_m120_network_import.sh",
    "m162_verify_network_bootstrap.py": ROOT / "scripts/m162_verify_network_bootstrap.py",
    "M140_M120_SINGLE_CHAIN_BOARD_RESULT_01.json": ROOT / "deployment/mage_vl4b/M140_M120_SINGLE_CHAIN_BOARD_RESULT_01.json",
}


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def main() -> int:
    if OUTPUT.exists():
        raise RuntimeError("M162 bootstrap output already exists")
    temporary = OUTPUT.with_name(OUTPUT.name + f".partial-{os.getpid()}")
    temporary.mkdir(parents=True)
    entries = []
    try:
        for relative, source in SOURCES.items():
            target = temporary / relative
            shutil.copyfile(source, target)
            entries.append({"path": relative, "bytes": target.stat().st_size, "sha256": sha256(target)})
        manifest = {
            "date": "2026-09-01",
            "gate": "M162-M120-network-bootstrap",
            "status": "PASS",
            "candidate_build_id": "0x4D395832",
            "m140_result_sha256": "60bc5dad7f3609c32b4698ebbb372eba9a3ab9e74b273969dd322299b4431cbb",
            "temporary_pc_ip": "192.168.0.10/24",
            "temporary_board_ip": "192.168.0.2/24",
            "files": entries,
            "file_count": len(entries),
        }
        (temporary / "PACKAGE_MANIFEST.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
        os.replace(temporary, OUTPUT)
    except BaseException:
        if temporary.exists():
            shutil.rmtree(temporary)
        raise
    result = {
        "date": "2026-09-01",
        "gate": "M162-M120-network-bootstrap-build-v2",
        "status": "PASS",
        "classification": "Clean network-control bootstrap only; no COM3 upload, IP change, weight transfer or FPGA execution.",
        "directory": OUTPUT.relative_to(ROOT).as_posix(),
        "package_manifest_sha256": sha256(OUTPUT / "PACKAGE_MANIFEST.json"),
        "file_count": len(entries),
        "total_bytes": sum(path.stat().st_size for path in OUTPUT.iterdir() if path.is_file()),
        "board_state_changed": False,
    }
    RESULT.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, indent=2))
    print("M162_NETWORK_BOOTSTRAP_BUILD_PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
