#!/usr/bin/env python3
"""Build and verify a clean M120 Layer-0 board package for post-M140 use."""

from __future__ import annotations

import hashlib
import json
import os
import shutil
import sys
from pathlib import Path


sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "deployment" / "mage_vl4b" / "m120_text4b_full_runtime"
DEST = ROOT / "deployment" / "mage_vl4b" / "m120_text4b_layer0_board_candidate"
M142 = ROOT / "deployment" / "mage_vl4b" / "M142_M120_FULL_RUNTIME_SOURCE_RESULT.json"
M143 = ROOT / "deployment" / "mage_vl4b" / "M143_M120_LAYER0_BOUNDARY_FIXTURE_RESULT.json"
FIXTURE = ROOT / "deployment" / "mage_vl4b" / "artifacts" / "m143_m120_layer0_boundaries.npz"
RESULT = ROOT / "deployment" / "mage_vl4b" / "M145_M120_LAYER0_BOARD_PACKAGE_RESULT.json"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(8 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def atomic_json(path: Path, payload: dict) -> None:
    temporary = path.with_suffix(path.suffix + f".tmp-{os.getpid()}")
    temporary.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    os.replace(temporary, path)


def main() -> int:
    result = {
        "date": "2026-09-01",
        "gate": "M145-M120-layer0-board-package",
        "status": "FAIL",
        "classification": "offline package identity gate; execution remains locked behind M140",
        "board_state_changed": False,
        "stable_rollback_preserved": True,
    }
    try:
        if DEST.exists():
            raise RuntimeError(f"destination already exists; refuse in-place mutation: {DEST}")
        m142 = json.loads(M142.read_text(encoding="utf-8"))
        m143 = json.loads(M143.read_text(encoding="utf-8"))
        if m142.get("status") != "PASS" or m143.get("status") != "PASS":
            raise RuntimeError("M142/M143 prerequisite status mismatch")
        if m142.get("source_manifest_sha256") != sha256(SOURCE / "SOURCE_MANIFEST.json"):
            raise RuntimeError("M142 source identity mismatch")
        if m143.get("fixture_sha256") != sha256(FIXTURE):
            raise RuntimeError("M143 fixture identity mismatch")

        shutil.copytree(
            SOURCE,
            DEST,
            copy_function=shutil.copyfile,
            ignore=shutil.ignore_patterns("__pycache__", "*.pyc", "*.log", "*.tmp"),
        )
        reference = DEST / "reference"
        reference.mkdir()
        shutil.copyfile(FIXTURE, reference / FIXTURE.name)
        shutil.copyfile(M143, reference / M143.name)

        files = []
        for path in sorted(DEST.rglob("*")):
            if not path.is_file() or path.name == "PACKAGE_MANIFEST.json":
                continue
            relative = path.relative_to(DEST).as_posix()
            if "__pycache__" in path.parts or path.suffix == ".pyc" or path.suffix == ".log":
                raise RuntimeError(f"forbidden package path: {relative}")
            files.append({
                "path": relative,
                "bytes": path.stat().st_size,
                "sha256": sha256(path),
            })
        manifest = {
            "date": "2026-09-01",
            "gate": "M145-M120-layer0-board-package",
            "status": "OFFLINE_PACKAGE_PASS_BOARD_NOT_EXECUTED",
            "build_id": "0x4D395832",
            "kernel": "mage_m120_m89x2_0",
            "weight_mode": "staged-low-cma",
            "source_manifest_sha256": m142["source_manifest_sha256"],
            "m143_result_sha256": sha256(M143),
            "m143_fixture_sha256": m143["fixture_sha256"],
            "required_predecessor": "M140_M120_SINGLE_CHAIN_BOARD_RESULT_01.json status=PASS",
            "files": files,
            "board_state_changed": False,
            "stable_rollback_preserved": True,
        }
        atomic_json(DEST / "PACKAGE_MANIFEST.json", manifest)
        package_sha = sha256(DEST / "PACKAGE_MANIFEST.json")

        declared = {item["path"] for item in files}
        observed = {
            path.relative_to(DEST).as_posix()
            for path in DEST.rglob("*")
            if path.is_file() and path.name != "PACKAGE_MANIFEST.json"
        }
        if declared != observed:
            raise RuntimeError("post-package whitelist closure mismatch")
        for item in files:
            path = DEST / item["path"]
            if path.stat().st_size != item["bytes"] or sha256(path) != item["sha256"]:
                raise RuntimeError(f"post-package file identity mismatch: {item['path']}")

        result.update(
            {
                "status": "PASS",
                "candidate": str(DEST.relative_to(ROOT).as_posix()),
                "package_manifest_sha256": package_sha,
                "file_count": len(files),
                "total_bytes": sum(item["bytes"] for item in files),
                "build_id": "0x4D395832",
                "kernel": "mage_m120_m89x2_0",
                "m143_result_sha256": sha256(M143),
                "m143_fixture_sha256": m143["fixture_sha256"],
                "next_gate": "Do not upload or execute until M140 single-chain PASS; then stage this package and the hash-audited full M120 payload via USB before M144 Layer-0.",
            }
        )
    except BaseException as error:
        result["error"] = f"{type(error).__name__}: {error}"
        result["next_gate"] = "Correct and rerun M145 offline only."
    atomic_json(RESULT, result)
    print(json.dumps(result, indent=2))
    print("M145_M120_LAYER0_BOARD_PACKAGE_PASS" if result["status"] == "PASS" else "M145_M120_LAYER0_BOARD_PACKAGE_FAIL")
    return 0 if result["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
