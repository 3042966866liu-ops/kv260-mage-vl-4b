#!/usr/bin/env python3
"""Build the clean four-member M184 COM3 receiver bootstrap."""

from __future__ import annotations

import hashlib
import json
import os
import shutil
import sys
from pathlib import Path


sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "tmp/m184_video_network/m184_bootstrap"
RESULT = ROOT / "deployment/mage_vl4b/M184_M181_VIDEO_PUSH_BOOTSTRAP_RESULT.json"
M182 = ROOT / "deployment/mage_vl4b/M182_M181_VIDEO_CANDIDATE_OFFLINE_GATE_RESULT.json"
EXPECTED_M182_SHA = "da6c69cb91a3956def857616f16d45358dd909b90967e110ad7e3a451b7e4f50"
EXPECTED_PACKAGE_SHA = "1596536bfe6865cb7eab5c038d8b4da8b666afc7cbd629ddc4559781727151d6"


def sha256(path: Path) -> str:
    value = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(4 << 20), b""):
            value.update(block)
    return value.hexdigest()


def atomic_json(path: Path, value: dict) -> None:
    temporary = path.with_name(path.name + ".partial")
    temporary.write_text(json.dumps(value, indent=2) + "\n", encoding="utf-8")
    os.replace(temporary, path)


def main() -> int:
    predecessor = json.loads(M182.read_text(encoding="utf-8"))
    if sha256(M182) != EXPECTED_M182_SHA or predecessor.get("status") != "PASS_OFFLINE_VIDEO_CANDIDATE_BOARD_NOT_EXECUTED":
        raise RuntimeError("M184 exact M182 identity mismatch")
    if predecessor.get("package_manifest_sha256") != EXPECTED_PACKAGE_SHA:
        raise RuntimeError("M184 exact M181 package identity mismatch")
    if OUTPUT.exists() or OUTPUT.with_name(OUTPUT.name + ".partial").exists():
        raise RuntimeError("M184 clean bootstrap output required")
    staging = OUTPUT.with_name(OUTPUT.name + ".partial")
    staging.mkdir(parents=True)
    sources = {
        "m184_video_board_receiver.py": ROOT / "scripts/m184_video_board_receiver.py",
        "m184_run_video_push_receiver.sh": ROOT / "scripts/m184_run_video_push_receiver.sh",
        "m184_verify_video_push_bootstrap.py": ROOT / "scripts/m184_verify_video_push_bootstrap.py",
        "M182_M181_VIDEO_CANDIDATE_OFFLINE_GATE_RESULT.json": M182,
    }
    entries = []
    for relative, source in sources.items():
        target = staging / relative
        shutil.copyfile(source, target)
        entries.append({"path": relative, "bytes": target.stat().st_size, "sha256": sha256(target)})
    manifest = {
        "date": "2026-09-01",
        "gate": "M184-M181-video-PC-push-bootstrap",
        "status": "PASS",
        "candidate_build_id": "0x4D395832",
        "m182_result_sha256": EXPECTED_M182_SHA,
        "video_package_manifest_sha256": EXPECTED_PACKAGE_SHA,
        "temporary_board_ip": "192.168.0.2/24",
        "pc_source_ip": "192.168.0.10",
        "listen_port": 8767,
        "files": entries,
        "file_count": len(entries),
    }
    (staging / "PACKAGE_MANIFEST.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    os.replace(staging, OUTPUT)
    result = {
        "date": "2026-09-01",
        "gate": "M184-M181-video-PC-push-bootstrap-build",
        "status": "PASS",
        "classification": "Clean COM3-controlled outbound-PC network bootstrap only; no upload, IP change, package transfer or FPGA execution.",
        "directory": OUTPUT.relative_to(ROOT).as_posix(),
        "package_manifest_sha256": sha256(OUTPUT / "PACKAGE_MANIFEST.json"),
        "m182_result_sha256": EXPECTED_M182_SHA,
        "video_package_manifest_sha256": EXPECTED_PACKAGE_SHA,
        "file_count": 4,
        "total_bytes": sum(item["bytes"] for item in entries),
        "windows_inbound_firewall_rule_required": False,
        "board_state_changed": False,
        "stable_rollback_preserved": True,
    }
    atomic_json(RESULT, result)
    print(json.dumps(result, indent=2))
    print("M184_VIDEO_PUSH_BOOTSTRAP_BUILD_PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
