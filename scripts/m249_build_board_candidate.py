#!/usr/bin/env python3
"""Build the clean hash-locked M249 KV260 SSDLite speed candidate."""

from __future__ import annotations

import hashlib
import json
import shutil
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "deployment/mage_vl4b/m249_ssdlite_board_source"
OUTPUT = ROOT / "deployment/mage_vl4b/m249_ssdlite_board_candidate"
RESULT = ROOT / "deployment/mage_vl4b/M249_SSDLITE_BOARD_CANDIDATE_OFFLINE_RESULT.json"

PREDECESSORS = {
    "m193_runtime_repair": (
        ROOT / "deployment/mage_vl4b/M193_PILLOW_RUNTIME_REPAIR_RESULT_01.json",
        "PASS",
    ),
    "m248_fast_safety_contract": (
        ROOT / "deployment/mage_vl4b/M248_FAST_SAFETY_OFFLINE_RESULT.json",
        "PASS_INTERFACE_AND_WEB_CONTRACT_ONLY",
    ),
    "m249_baseline_selection": (
        ROOT / "deployment/mage_vl4b/M249_SSDLITE_BASELINE_SELECTION_RESULT.json",
        "MEASURED_CONTINUE_TO_BOARD_SPEED_GATE",
    ),
    "m249_host_codepath": (
        ROOT / "deployment/mage_vl4b/M249_SSDLITE_HOST_CODEPATH_RESULT.json",
        "PASS_HOST_CODEPATH",
    ),
}

WHITELIST = {
    "run_m249_board_gate.sh",
    "runtime/m249_board_probe.py",
    "fixtures/FIXTURE_MANIFEST.json",
    "fixtures/frame_00_0068_rgb448.npy",
    "fixtures/frame_01_0102_rgb448.npy",
    "fixtures/frame_02_0137_rgb448.npy",
    "fixtures/frame_03_0171_rgb448.npy",
    "model/ssdlite320_mobilenet_v3_large_coco-a79551df.pth",
    "wheels/torchvision-0.27.1+cpu-cp310-cp310-manylinux_2_28_aarch64.whl",
}


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(4 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def write_json(path: Path, value: dict) -> None:
    path.write_text(json.dumps(value, indent=2) + "\n", encoding="utf-8")


def main() -> int:
    if OUTPUT.exists():
        raise RuntimeError(f"clean output required: {OUTPUT}")
    actual_source = {
        path.relative_to(SOURCE).as_posix()
        for path in SOURCE.rglob("*")
        if path.is_file()
    }
    if actual_source != WHITELIST:
        raise RuntimeError(f"source whitelist mismatch: missing={WHITELIST-actual_source}, extra={actual_source-WHITELIST}")
    if any(path.is_symlink() for path in SOURCE.rglob("*")):
        raise RuntimeError("symlink forbidden")

    predecessor_records = {}
    for name, (path, expected_status) in PREDECESSORS.items():
        value = json.loads(path.read_text(encoding="utf-8"))
        if value.get("status") != expected_status:
            raise RuntimeError(f"predecessor status mismatch: {name}")
        predecessor_records[name] = {
            "path": path.relative_to(ROOT).as_posix(),
            "status": expected_status,
            "sha256": sha256(path),
        }

    OUTPUT.mkdir(parents=True)
    for relative in sorted(WHITELIST):
        source = SOURCE / relative
        target = OUTPUT / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, target)

    predecessor = {
        "gate": "M249-KV260-SSDLite-board-candidate-predecessor-summary",
        "status": "PASS",
        "predecessors": predecessor_records,
        "stable_t32_overlay_preserved": True,
        "board_execution_run": False,
    }
    write_json(OUTPUT / "M249_PREDECESSOR_SUMMARY.json", predecessor)

    payload_paths = sorted(path for path in OUTPUT.rglob("*") if path.is_file())
    files = []
    for path in payload_paths:
        relative = path.relative_to(OUTPUT).as_posix()
        if "__pycache__" in path.parts or path.suffix == ".pyc":
            raise RuntimeError(f"cache forbidden: {relative}")
        files.append({"path": relative, "bytes": path.stat().st_size, "sha256": sha256(path)})
    manifest = {
        "date": "2026-09-02",
        "gate": "M249-KV260-A53-SSDLite-person-knife-speed-candidate",
        "status": "PASS",
        "classification": "Hash-locked board speed candidate only; not executed and not accuracy, action, Web, FPGA or real-time evidence.",
        "destination": "/home/ubuntu/tellme_m120_m89x2_20260901/m249_ssdlite_board_candidate",
        "file_count": len(files),
        "total_bytes": sum(item["bytes"] for item in files),
        "files": files,
    }
    manifest_path = OUTPUT / "PACKAGE_MANIFEST.json"
    write_json(manifest_path, manifest)
    manifest_sha = sha256(manifest_path)
    ready = {
        "gate": manifest["gate"],
        "status": "READY",
        "package_manifest_sha256": manifest_sha,
        "file_count": len(files),
        "total_bytes": manifest["total_bytes"],
    }
    write_json(OUTPUT / "PACKAGE_READY.json", ready)

    result = {
        "date": "2026-09-02",
        "gate": "M249-KV260-A53-SSDLite-board-candidate-offline",
        "status": "PASS_OFFLINE_BOARD_CANDIDATE_NOT_EXECUTED",
        "classification": "Clean package, dependency and host-codepath evidence only; not board, accuracy, action, Web, FPGA or real-time PASS.",
        "package_directory": OUTPUT.relative_to(ROOT).as_posix(),
        "package_manifest_sha256": manifest_sha,
        "file_count": len(files),
        "total_bytes": manifest["total_bytes"],
        "model_checkpoint_sha256": "a79551df90c79834bcd3bb3845ef9d966b5449a3a9b2833ae8404778ca5d65d2",
        "arm64_torchvision_wheel_sha256": "3323edb900ca46d29dba267ee809e55fe5fe09cd3d9f54124a7c5ed33a6a2dbe",
        "fixture_manifest_sha256": sha256(OUTPUT / "fixtures/FIXTURE_MANIFEST.json"),
        "predecessors": predecessor_records,
        "board_execution_run": False,
        "stable_t32_overlay_preserved": True,
        "next_gate": "Transfer through COM3-controlled temporary direct Ethernet, verify every hash, then run only the M249 A53 speed gate.",
    }
    write_json(RESULT, result)
    print(json.dumps(result, indent=2))
    print("M249_SSDLITE_BOARD_CANDIDATE_OFFLINE_PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
