#!/usr/bin/env python3
"""Build the clean M222 ARM64 decoder micro-gate package."""

from __future__ import annotations

import hashlib
import json
import os
import shutil
import sys
from pathlib import Path


sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "tmp/m222_decoder/m222_decoder_microgate"
RESULT = ROOT / "deployment/mage_vl4b/M222_ARM64_DECODER_PACKAGE_RESULT.json"
OFFLINE = ROOT / "deployment/mage_vl4b/M222_VECTORIZED_W4_DECODE_OFFLINE_RESULT.json"
VISION = ROOT / "deployment/mage_vl4b/M222_PS_VISION_OFFLINE_RESULT.json"


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> int:
    offline = json.loads(OFFLINE.read_text(encoding="utf-8"))
    vision = json.loads(VISION.read_text(encoding="utf-8"))
    if not (
        offline.get("status") == "PASS"
        and offline.get("bit_exact") is True
        and offline.get("module_count") == 98
        and vision.get("status") == "PASS"
        and vision.get("model_math_changed") is False
    ):
        raise RuntimeError("M222 offline predecessor closure mismatch")
    partial = OUT.with_name(OUT.name + ".partial")
    if OUT.exists():
        shutil.rmtree(OUT)
    if partial.exists():
        shutil.rmtree(partial)
    partial.mkdir(parents=True)
    sources = {
        "m222_vectorized_w4_runtime.py": ROOT / "deployment/mage_vl4b/m222_realtime_vision_source/m222_vectorized_w4_runtime.py",
        "m222_board_decode_microbench.py": ROOT / "scripts/m222_board_decode_microbench.py",
        "m222_verify_board_delta.py": ROOT / "scripts/m222_verify_board_delta.py",
        "m222_run_board_decode_microbench.sh": ROOT / "scripts/m222_run_board_decode_microbench.sh",
        "M222_VECTORIZED_W4_DECODE_OFFLINE_RESULT.json": OFFLINE,
        "M222_PS_VISION_OFFLINE_RESULT.json": VISION,
    }
    for name, source in sources.items():
        destination = partial / name
        shutil.copyfile(source, destination)
    entries = []
    for path in sorted(item for item in partial.rglob("*") if item.is_file()):
        entries.append({
            "path": path.relative_to(partial).as_posix(),
            "bytes": path.stat().st_size,
            "sha256": sha(path),
        })
    manifest = {
        "date": "2026-09-01",
        "gate": "M222-ARM64-decoder-microgate-package",
        "status": "PASS",
        "build_id": "0x4D395832",
        "offline_decoder_result_sha256": sha(OFFLINE),
        "offline_vision_result_sha256": sha(VISION),
        "files": entries,
        "file_count": len(entries),
        "total_bytes": sum(item["bytes"] for item in entries),
        "board_state_changed": False,
        "stable_rollback_preserved": True,
    }
    (partial / "PACKAGE_MANIFEST.json").write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    os.replace(partial, OUT)
    result = {
        "date": "2026-09-01",
        "gate": "M222-ARM64-decoder-microgate-package-build",
        "status": "PASS",
        "directory": OUT.relative_to(ROOT).as_posix(),
        "package_manifest_sha256": sha(OUT / "PACKAGE_MANIFEST.json"),
        "file_count": len(entries),
        "total_bytes": manifest["total_bytes"],
        "board_state_changed": False,
        "next_gate": "Manifest-first COM3 upload and ARM64 decoder-only gate.",
    }
    RESULT.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print("M222_ARM64_DECODER_PACKAGE_PASS")
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

