#!/usr/bin/env python3
"""Build the clean five-member M166 board delta."""

from __future__ import annotations

import hashlib
import json
import os
import shutil
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "deployment/mage_vl4b/m165_m120_layer0_board_candidate"
OUTPUT = ROOT / "tmp/m166_layer0/m166_delta_01"
RESULT = ROOT / "deployment/mage_vl4b/M166_M120_CORRECTED_LAYER0_DELTA_RESULT.json"


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> int:
    if OUTPUT.exists() or OUTPUT.with_name(OUTPUT.name + ".partial").exists():
        raise RuntimeError("M166 clean delta output required")
    staging = OUTPUT.with_name(OUTPUT.name + ".partial")
    staging.mkdir(parents=True)
    sources = {
        "m166_apply_corrected_layer0_delta.py": ROOT / "scripts/m166_apply_corrected_layer0_delta.py",
        "PACKAGE_MANIFEST.json": SOURCE / "PACKAGE_MANIFEST.json",
        "SOURCE_MANIFEST.json": SOURCE / "SOURCE_MANIFEST.json",
        "auxiliary/M77_TEXT_AUX_MANIFEST.json": SOURCE / "auxiliary/M77_TEXT_AUX_MANIFEST.json",
        "auxiliary/m77_text_aux_fp16.npz": SOURCE / "auxiliary/m77_text_aux_fp16.npz",
    }
    entries = []
    for relative, source in sources.items():
        target = staging / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source, target)
        entries.append({"path": relative, "bytes": target.stat().st_size, "sha256": sha256(target)})
    manifest = {
        "date": "2026-09-01",
        "gate": "M166-M120-corrected-Layer0-delta",
        "status": "PASS",
        "candidate_build_id": "0x4D395832",
        "source_package_manifest_sha256": "732b881d3507eaa12b8488e9224835ac115b686a003c748c9fa05a9793041d13",
        "target_package_manifest_sha256": "34662ca90cb45b9a1d34903538b030f28b1f9f70ece3f35e7ccbbaf6eb3bbf97",
        "files": entries,
        "file_count": len(entries),
    }
    (staging / "DELTA_MANIFEST.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    os.replace(staging, OUTPUT)
    result = {
        "date": "2026-09-01",
        "gate": "M166-M120-corrected-Layer0-delta-build",
        "status": "PASS",
        "classification": "Offline delta package only; no COM3, board or FPGA execution.",
        "directory": OUTPUT.relative_to(ROOT).as_posix(),
        "delta_manifest_sha256": sha256(OUTPUT / "DELTA_MANIFEST.json"),
        "file_count": len(entries),
        "total_bytes": sum(item["bytes"] for item in entries),
        "board_state_changed": False,
    }
    RESULT.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, indent=2))
    print("M166_CORRECTED_LAYER0_DELTA_BUILD_PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
