#!/usr/bin/env python3
"""Build the clean five-member M176 host-runtime delta."""

from __future__ import annotations

import hashlib
import json
import os
import shutil
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "deployment/mage_vl4b/m175_m120_fixed_text_candidate"
OUTPUT = ROOT / "tmp/m176_fixed_text/m176_delta_01"
RESULT = ROOT / "deployment/mage_vl4b/M176_M120_LMHEAD_OPTIONAL_LAYER_DELTA_RESULT.json"


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> int:
    if OUTPUT.exists() or RESULT.exists():
        raise RuntimeError("M176 clean output required")
    staging = OUTPUT.with_name(OUTPUT.name + f".partial-{os.getpid()}")
    staging.mkdir(parents=True)
    sources = {
        "m176_apply_lmhead_optional_layer_delta.py": ROOT / "scripts/m176_apply_lmhead_optional_layer_delta.py",
        "PACKAGE_MANIFEST.json": SOURCE / "PACKAGE_MANIFEST.json",
        "SOURCE_MANIFEST.json": SOURCE / "SOURCE_MANIFEST.json",
        "runtime/board_runtime.py": SOURCE / "runtime/board_runtime.py",
        "runtime/text_e2e_gate.py": SOURCE / "runtime/text_e2e_gate.py",
    }
    entries = []
    try:
        for relative, source in sources.items():
            target = staging / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(source, target)
            entries.append({"path": relative, "bytes": target.stat().st_size, "sha256": digest(target)})
        manifest = {
            "date": "2026-09-01",
            "gate": "M176-M120-LMHead-optional-layer-delta",
            "status": "PASS",
            "candidate_build_id": "0x4D395832",
            "source_package_manifest_sha256": "34662ca90cb45b9a1d34903538b030f28b1f9f70ece3f35e7ccbbaf6eb3bbf97",
            "target_package_manifest_sha256": "406dcca340e4604baeb761445795391c43ec26bd99fa06ffae893d597b17414f",
            "files": entries,
            "file_count": len(entries),
        }
        (staging / "DELTA_MANIFEST.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
        os.replace(staging, OUTPUT)
    except Exception:
        if staging.exists():
            shutil.rmtree(staging)
        raise
    result = {
        "date": "2026-09-01",
        "gate": "M176-M120-LMHead-optional-layer-delta-build",
        "status": "PASS",
        "classification": "Offline delta only; no COM3, board or FPGA execution.",
        "directory": OUTPUT.relative_to(ROOT).as_posix(),
        "delta_manifest_sha256": digest(OUTPUT / "DELTA_MANIFEST.json"),
        "file_count": len(entries),
        "total_bytes": sum(item["bytes"] for item in entries),
        "board_state_changed": False,
    }
    RESULT.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, indent=2))
    print("M176_LMHEAD_OPTIONAL_LAYER_DELTA_BUILD_PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
