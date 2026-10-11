#!/usr/bin/env python3
"""Build a clean, hash-closed M239 full-849 Prefill profile delta."""
from __future__ import annotations

import hashlib
import json
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "deployment/mage_vl4b/m239_full849_profile_source"
M230 = ROOT / "deployment/mage_vl4b/m230_prefill_stage_once_source"
M231 = ROOT / "deployment/mage_vl4b/m231_prefill_parse_reuse_source"
M236 = ROOT / "deployment/mage_vl4b/m236_fused_parse_overlap_source"
M238 = ROOT / "deployment/mage_vl4b/m238_input_prefetch_source"
OUTPUT = ROOT / "deployment/mage_vl4b/m239_full849_profile_board_candidate"
PREDECESSOR = ROOT / "deployment/mage_vl4b/M238_INPUT_PREFETCH_BOARD_RESULT_02.json"
RESULT = ROOT / "deployment/mage_vl4b/M239_FULL849_PROFILE_BOARD_DELTA_RESULT.json"
FILES = (
    (M230 / "m230_prefill_runtime.py", "m230_prefill_runtime.py"),
    (M231 / "m231_prefill_runtime.py", "m231_prefill_runtime.py"),
    (M236 / "m236_prefill_runtime.py", "m236_prefill_runtime.py"),
    (M238 / "m238_prefill_runtime.py", "m238_prefill_runtime.py"),
    (M230 / "m230_video_language_runtime.py", "m230_video_language_runtime.py"),
    (SOURCE / "m239_full849_profile.py", "m239_full849_profile.py"),
    (M230 / "m230_verify_package.py", "m230_verify_package.py"),
    (SOURCE / "run_m239_board_gate.sh", "run_m239_board_gate.sh"),
)


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> int:
    if OUTPUT.exists() or OUTPUT.with_name(OUTPUT.name + ".partial").exists():
        raise RuntimeError(f"M239 clean output required: {OUTPUT}")
    predecessor = json.loads(PREDECESSOR.read_text(encoding="utf-8"))
    if predecessor.get("status") != "PASS" or predecessor.get("gate") != "M238-real-KV260-input-pack-prefetch-acceptance":
        raise RuntimeError("M238 board predecessor mismatch")
    partial = OUTPUT.with_name(OUTPUT.name + ".partial")
    partial.mkdir(parents=True)
    records = []
    for source, relative in FILES:
        if not source.is_file():
            raise RuntimeError(f"M239 missing source: {source}")
        destination = partial / relative
        shutil.copy2(source, destination)
        records.append({"path": relative, "bytes": destination.stat().st_size, "sha256": sha(destination)})
    forbidden = [
        path.relative_to(partial).as_posix()
        for path in partial.rglob("*")
        if path.is_file() and (path.suffix == ".pyc" or "__pycache__" in path.parts)
    ]
    if forbidden:
        raise RuntimeError(f"M239 forbidden files: {forbidden}")
    manifest = {
        "date": "2026-09-01",
        "gate": "M239-complete-849-language-prefill-profile-board-delta",
        "status": "PASS",
        "classification": "Measurement-only full 849-token language Prefill profile over accepted M238; independent of T64 and no bitstream, weight, model-math, boot, DTB, CMA, partition, or persistent-service mutation.",
        "base_build_id": "0x4D395832",
        "base_package_manifest_sha256": "406dcca340e4604baeb761445795391c43ec26bd99fa06ffae893d597b17414f",
        "m238_predecessor_sha256": sha(PREDECESSOR),
        "files": records,
        "file_count": len(records),
        "total_file_bytes": sum(record["bytes"] for record in records),
        "forbidden_cache_file_count": 0,
        "board_state_changed": False,
    }
    manifest_path = partial / "PACKAGE_MANIFEST.json"
    manifest_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    partial.replace(OUTPUT)
    result = {
        "date": "2026-09-01",
        "gate": "M239-complete-849-language-prefill-profile-board-delta-build",
        "status": "PASS",
        "directory": OUTPUT.relative_to(ROOT).as_posix(),
        "package_manifest_sha256": sha(OUTPUT / "PACKAGE_MANIFEST.json"),
        "file_count": len(records),
        "total_file_bytes": manifest["total_file_bytes"],
        "board_state_changed": False,
        "next_gate": "COM3 one complete deterministic 849-token language Prefill profile; require 36 layers, 154 families, 4158 T32 blocks, 4166 logical calls, finite output/cache, exact Build ID, and service restoration.",
    }
    partial_result = RESULT.with_name(RESULT.name + ".partial")
    partial_result.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    partial_result.replace(RESULT)
    print(json.dumps(result, indent=2))
    print("M239_FULL849_PROFILE_BOARD_DELTA_BUILD_PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
