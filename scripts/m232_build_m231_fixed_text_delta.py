#!/usr/bin/env python3
"""Build a clean M232 M231-fixed-text runtime delta."""

from __future__ import annotations

import hashlib
import json
import shutil
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "deployment/mage_vl4b/m232_m231_fixed_text_source"
M230 = ROOT / "deployment/mage_vl4b/m230_prefill_stage_once_source"
M231 = ROOT / "deployment/mage_vl4b/m231_prefill_parse_reuse_source"
M231_RESULT = ROOT / "deployment/mage_vl4b/M231_PARSE_REUSE_BOARD_RESULT_02.json"
OUTPUT = ROOT / "deployment/mage_vl4b/m232_m231_fixed_text_board_candidate"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def main() -> int:
    if OUTPUT.exists():
        raise RuntimeError(f"M232 clean output already exists: {OUTPUT}")
    m231_formal = json.loads(M231_RESULT.read_text(encoding="utf-8"))
    if m231_formal.get("status") != "PASS":
        raise RuntimeError("M232 requires the exact M231 formal PASS")
    family_bytes = (json.dumps(m231_formal["family"], indent=2) + "\n").encode("utf-8")
    predecessor = {
        "date": "2026-09-01",
        "gate": "M232-M231-exact-board-predecessor",
        "status": "PASS",
        "m231_formal_result_sha256": sha256(M231_RESULT),
        "board_family_measurement_sha256": hashlib.sha256(family_bytes).hexdigest(),
        "build_id": "0x4D395832",
        "tokens": 849,
        "output_sha256_fp32": "ec6d680770fbac413cf51076656f206defc78edf4e92cfb41fc1a60c58d1f81e",
    }
    OUTPUT.mkdir(parents=True)
    sources = (
        (M230 / "m230_prefill_runtime.py", "m230_prefill_runtime.py"),
        (M231 / "m231_prefill_runtime.py", "m231_prefill_runtime.py"),
        (SOURCE / "m231_fixed_text_gate.py", "m231_fixed_text_gate.py"),
        (SOURCE / "m232_verify_predecessor.py", "m232_verify_predecessor.py"),
        (SOURCE / "m232_accept_fixed_text.py", "m232_accept_fixed_text.py"),
        (M230 / "m230_verify_package.py", "m230_verify_package.py"),
        (SOURCE / "run_m232_fixed_text_gate.sh", "run_m232_fixed_text_gate.sh"),
    )
    for source, relative in sources:
        shutil.copy2(source, OUTPUT / relative)
    (OUTPUT / "M231_PREDECESSOR_SUMMARY.json").write_text(
        json.dumps(predecessor, indent=2) + "\n", encoding="utf-8"
    )
    records = []
    for path in sorted(OUTPUT.iterdir()):
        if path.name == "PACKAGE_MANIFEST.json":
            continue
        records.append({"path": path.name, "bytes": path.stat().st_size, "sha256": sha256(path)})
    manifest = {
        "date": "2026-09-01",
        "gate": "M232-M231-fixed-text-runtime-board-delta",
        "status": "PASS",
        "classification": "Clean runtime-only M231 fixed-text delta; no bitstream, weights, quantization, boot, DTB, CMA, partition, or persistent service mutation.",
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
        "gate": "M232-M231-fixed-text-board-delta-build",
        "status": "PASS",
        "directory": OUTPUT.relative_to(ROOT).as_posix(),
        "package_manifest_sha256": sha256(manifest_path),
        "file_count": len(records),
        "total_file_bytes": manifest["total_file_bytes"],
        "board_state_changed": False,
        "next_gate": "COM3 exact M231 predecessor check and frozen fixed-text 4B E2E only.",
    }
    (ROOT / "deployment/mage_vl4b/M232_M231_FIXED_TEXT_BOARD_DELTA_RESULT.json").write_text(
        json.dumps(result, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps(result, indent=2))
    print("M232_M231_FIXED_TEXT_BOARD_DELTA_BUILD_PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
