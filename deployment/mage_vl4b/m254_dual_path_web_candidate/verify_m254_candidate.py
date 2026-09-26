#!/usr/bin/env python3
"""Fail-closed verifier for the staged M254 board delta."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(4 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--expected-manifest-sha256", required=True)
    args = parser.parse_args()
    root = args.root.resolve()
    allowed = Path("/home/ubuntu/tellme_m120_m89x2_20260901/m254_dual_path_web_candidate").resolve()
    if root != allowed:
        raise RuntimeError(f"M254 refused root {root}")
    manifest_path = root / "PACKAGE_MANIFEST.json"
    if sha256(manifest_path) != args.expected_manifest_sha256:
        raise RuntimeError("M254 manifest hash mismatch")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if manifest.get("gate") != "M254-dual-path-Web-board-candidate" or manifest.get("status") != "PASS":
        raise RuntimeError("M254 manifest identity mismatch")
    records = manifest.get("files")
    if not isinstance(records, list) or len(records) != manifest.get("file_count"):
        raise RuntimeError("M254 manifest count mismatch")
    expected = sorted(item["path"] for item in records)
    observed = sorted(path.relative_to(root).as_posix() for path in root.rglob("*") if path.is_file() and path.name != "PACKAGE_MANIFEST.json")
    if observed != expected:
        raise RuntimeError(f"M254 file closure mismatch observed={observed} expected={expected}")
    for item in records:
        path = root / item["path"]
        if path.stat().st_size != item["bytes"] or sha256(path) != item["sha256"]:
            raise RuntimeError(f"M254 payload mismatch {item['path']}")
    if any(path.suffix == ".pyc" or "__pycache__" in path.parts for path in root.rglob("*")):
        raise RuntimeError("M254 forbidden bytecode/cache path")
    predecessors = manifest.get("predecessors", {})
    for name, expected_sha in (
        ("M243_WEB_PREFILL_BOARD_RESULT_05.json", predecessors.get("m243_board_result_sha256")),
        ("M253_KV260_LATEST_FAST_STREAM_BOARD_RESULT_02.json", predecessors.get("m253_board_result_sha256")),
        ("M249_KV260_SSDLITE_BOARD_RESULT_03.json", predecessors.get("m249_board_result_sha256")),
    ):
        if not expected_sha or sha256(root / name) != expected_sha:
            raise RuntimeError(f"M254 predecessor mismatch {name}")
    required_modules = {
        "fast_frame_pipeline.py", "fast_safety_monitor.py", "immediate_safety_monitor.py",
        "knife_alarm.py", "latest_fast_stream.py", "m253_board_latest_stream.py",
        "m254_dual_path_core.py", "m254_video_server.py", "temporal_action_adapter.py",
    }
    if not required_modules.issubset(set(observed)):
        raise RuntimeError("M254 recursive local-module closure incomplete")
    print(json.dumps({
        "gate": "M254-staged-package-closure",
        "status": "PASS",
        "manifest_sha256": args.expected_manifest_sha256,
        "file_count": len(records),
        "total_bytes": sum(item["bytes"] for item in records),
    }, indent=2))
    print("M254_STAGED_PACKAGE_VERIFY_PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

