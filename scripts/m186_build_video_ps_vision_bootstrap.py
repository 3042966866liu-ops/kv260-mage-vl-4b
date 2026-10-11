#!/usr/bin/env python3
"""Build a clean four-member M186 PS-vision gate bootstrap."""

from __future__ import annotations

import hashlib
import json
import os
import shutil
import sys
from pathlib import Path


sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "tmp/m186_ps_vision/m186_gate"
RESULT = ROOT / "deployment/mage_vl4b/M186_M181_PS_VISION_BOOTSTRAP_RESULT.json"
M184 = ROOT / "deployment/mage_vl4b/M184_M181_VIDEO_BOARD_IMPORT_RESULT_01.json"
EXPECTED_M184_SHA = "790bae8a261156e95b23d7aa349d9410dc3d511388a94ad9be80106ce8a2cf84"
EXPECTED_PACKAGE_SHA = "1596536bfe6865cb7eab5c038d8b4da8b666afc7cbd629ddc4559781727151d6"


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> int:
    predecessor = json.loads(M184.read_text(encoding="utf-8"))
    if sha256(M184) != EXPECTED_M184_SHA or predecessor.get("status") != "PASS" or predecessor.get("package_manifest_sha256") != EXPECTED_PACKAGE_SHA:
        raise RuntimeError("M186 exact M184 identity mismatch")
    if OUTPUT.exists() or OUTPUT.with_name(OUTPUT.name + ".partial").exists():
        raise RuntimeError("M186 clean bootstrap output required")
    staging = OUTPUT.with_name(OUTPUT.name + ".partial")
    staging.mkdir(parents=True)
    sources = {
        "m186_video_ps_vision_board_gate.py": ROOT / "scripts/m186_video_ps_vision_board_gate.py",
        "m186_run_video_ps_vision_board_gate.sh": ROOT / "scripts/m186_run_video_ps_vision_board_gate.sh",
        "m186_verify_video_ps_vision_bootstrap.py": ROOT / "scripts/m186_verify_video_ps_vision_bootstrap.py",
        "M184_M181_VIDEO_BOARD_IMPORT_RESULT_01.json": M184,
    }
    entries = []
    for relative, source in sources.items():
        target = staging / relative
        shutil.copyfile(source, target)
        entries.append({"path": relative, "bytes": target.stat().st_size, "sha256": sha256(target)})
    manifest = {
        "date": "2026-09-01",
        "gate": "M186-M181-PS-vision-board-gate-bootstrap",
        "status": "PASS",
        "candidate_build_id": "0x4D395832",
        "m184_formal_result_sha256": EXPECTED_M184_SHA,
        "video_package_manifest_sha256": EXPECTED_PACKAGE_SHA,
        "files": entries,
        "file_count": 4,
    }
    (staging / "PACKAGE_MANIFEST.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    os.replace(staging, OUTPUT)
    result = {
        "date": "2026-09-01",
        "gate": "M186-M181-PS-vision-board-gate-bootstrap-build",
        "status": "PASS",
        "classification": "Offline bootstrap only; no board numerical execution.",
        "directory": OUTPUT.relative_to(ROOT).as_posix(),
        "package_manifest_sha256": sha256(OUTPUT / "PACKAGE_MANIFEST.json"),
        "m184_formal_result_sha256": EXPECTED_M184_SHA,
        "video_package_manifest_sha256": EXPECTED_PACKAGE_SHA,
        "file_count": 4,
        "total_bytes": sum(item["bytes"] for item in entries),
        "board_state_changed": False,
        "stable_rollback_preserved": True,
    }
    temporary = RESULT.with_name(RESULT.name + ".partial")
    temporary.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    os.replace(temporary, RESULT)
    print(json.dumps(result, indent=2))
    print("M186_PS_VISION_BOOTSTRAP_BUILD_PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
