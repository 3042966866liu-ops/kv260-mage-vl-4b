#!/usr/bin/env python3
"""Build the clean M249 COM3-controlled direct-Ethernet bootstrap."""

from __future__ import annotations

import hashlib
import json
import shutil
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "tmp/m249_ssdlite_network/m249_bootstrap"
RESULT = ROOT / "deployment/mage_vl4b/M249_SSDLITE_TRANSFER_BOOTSTRAP_RESULT.json"
PACKAGE_RESULT = ROOT / "deployment/mage_vl4b/M249_SSDLITE_BOARD_CANDIDATE_OFFLINE_RESULT.json"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def write_json(path: Path, value: dict) -> None:
    path.write_text(json.dumps(value, indent=2) + "\n", encoding="utf-8")


def main() -> int:
    package_result = json.loads(PACKAGE_RESULT.read_text(encoding="utf-8"))
    if package_result.get("status") != "PASS_OFFLINE_BOARD_CANDIDATE_NOT_EXECUTED":
        raise RuntimeError("exact M249 offline package predecessor required")
    if OUTPUT.exists():
        raise RuntimeError(f"clean bootstrap output required: {OUTPUT}")
    OUTPUT.mkdir(parents=True)
    members = {
        "M249_SSDLITE_BOARD_CANDIDATE_OFFLINE_RESULT.json": PACKAGE_RESULT,
        "m249_board_receiver.py": ROOT / "scripts/m249_board_receiver.py",
        "m249_run_receiver_and_gate.sh": ROOT / "scripts/m249_run_receiver_and_gate.sh",
        "m249_verify_bootstrap.py": ROOT / "scripts/m249_verify_bootstrap.py",
    }
    for name, source in members.items():
        shutil.copy2(source, OUTPUT / name)
    files = [
        {"path": name, "bytes": (OUTPUT / name).stat().st_size, "sha256": sha256(OUTPUT / name)}
        for name in sorted(members)
    ]
    manifest = {
        "date": "2026-09-02",
        "gate": "M249-KV260-SSDLite-transfer-bootstrap",
        "status": "PASS",
        "package_manifest_sha256": package_result["package_manifest_sha256"],
        "offline_result_sha256": sha256(PACKAGE_RESULT),
        "file_count": len(files),
        "total_bytes": sum(item["bytes"] for item in files),
        "files": files,
    }
    manifest_path = OUTPUT / "PACKAGE_MANIFEST.json"
    write_json(manifest_path, manifest)
    result = {
        "date": "2026-09-02",
        "gate": "M249-KV260-SSDLite-transfer-bootstrap-build",
        "status": "PASS",
        "classification": "Small COM3 bootstrap build only; no upload, board state change, detector execution or performance evidence.",
        "directory": OUTPUT.relative_to(ROOT).as_posix(),
        "package_manifest_sha256": sha256(manifest_path),
        "candidate_package_manifest_sha256": package_result["package_manifest_sha256"],
        "file_count": len(files),
        "total_bytes": manifest["total_bytes"],
        "board_state_changed": False,
        "stable_t32_overlay_preserved": True,
    }
    write_json(RESULT, result)
    print(json.dumps(result, indent=2))
    print("M249_TRANSFER_BOOTSTRAP_BUILD_PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
