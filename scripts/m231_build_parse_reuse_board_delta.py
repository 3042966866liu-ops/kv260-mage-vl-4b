#!/usr/bin/env python3
"""Build the clean, hash-locked M231 runtime-only board delta."""

from __future__ import annotations

import hashlib
import json
import shutil
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "deployment/mage_vl4b/m231_prefill_parse_reuse_source"
M230 = ROOT / "deployment/mage_vl4b/m230_prefill_stage_once_source"
OUTPUT = ROOT / "deployment/mage_vl4b/m231_parse_reuse_board_candidate"
FILES = (
    (M230 / "m230_prefill_runtime.py", "m230_prefill_runtime.py"),
    (SOURCE / "m231_prefill_runtime.py", "m231_prefill_runtime.py"),
    (SOURCE / "m231_board_gate.py", "m231_board_gate.py"),
    (M230 / "m230_verify_package.py", "m230_verify_package.py"),
    (SOURCE / "run_m231_board_gate.sh", "run_m231_board_gate.sh"),
)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def main() -> int:
    if OUTPUT.exists():
        raise RuntimeError(f"M231 clean output already exists: {OUTPUT}")
    OUTPUT.mkdir(parents=True)
    records = []
    for source, relative in FILES:
        if not source.is_file():
            raise RuntimeError(f"M231 missing source: {source}")
        destination = OUTPUT / relative
        shutil.copy2(source, destination)
        records.append({
            "path": relative,
            "bytes": destination.stat().st_size,
            "sha256": sha256(destination),
        })
    manifest = {
        "date": "2026-09-01",
        "gate": "M231-parse-reuse-runtime-board-delta",
        "status": "PASS",
        "classification": "Clean runtime-only delta for accepted M120 T32; no bitstream, weights, quantization, boot, DTB, CMA, partition, or persistent service mutation.",
        "base_build_id": "0x4D395832",
        "base_package_manifest_sha256": "406dcca340e4604baeb761445795391c43ec26bd99fa06ffae893d597b17414f",
        "files": records,
        "file_count": len(records),
        "total_file_bytes": sum(item["bytes"] for item in records),
        "forbidden_cache_file_count": 0,
        "board_state_changed": False,
    }
    manifest_path = OUTPUT / "PACKAGE_MANIFEST.json"
    manifest_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    result = {
        "date": "2026-09-01",
        "gate": "M231-parse-reuse-board-delta-build",
        "status": "PASS",
        "directory": OUTPUT.relative_to(ROOT).as_posix(),
        "package_manifest_sha256": sha256(manifest_path),
        "file_count": len(records),
        "total_file_bytes": manifest["total_file_bytes"],
        "board_state_changed": False,
        "next_gate": "COM3 exact package verification and one M230-versus-M231 849-token q_proj family bit-exact performance gate.",
    }
    result_path = ROOT / "deployment/mage_vl4b/M231_PARSE_REUSE_BOARD_DELTA_RESULT.json"
    result_path.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, indent=2))
    print("M231_PARSE_REUSE_BOARD_DELTA_BUILD_PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
