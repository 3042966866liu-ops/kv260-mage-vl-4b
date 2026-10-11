#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import json
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "deployment/mage_vl4b/m237r1_acceptance_repair_source"
M230_VERIFY = ROOT / "deployment/mage_vl4b/m230_prefill_stage_once_source/m230_verify_package.py"
M237_RESULT = ROOT / "deployment/mage_vl4b/M237_M236_FIXED_TEXT_BOARD_RESULT_01.json"
OUTPUT = ROOT / "deployment/mage_vl4b/m237r1_acceptance_repair_board_candidate"
BUILD_RESULT = ROOT / "deployment/mage_vl4b/M237R1_ACCEPTANCE_REPAIR_DELTA_RESULT.json"


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> int:
    if OUTPUT.exists():
        raise RuntimeError("M237R1 clean output required")
    m237 = json.loads(M237_RESULT.read_text())
    fixed = m237["fixed_text"]
    if fixed.get("status") != "PASS" or fixed.get("generated_token_id") != 17:
        raise RuntimeError("M237R1 requires immutable inner fixed-text PASS")

    partial = OUTPUT.with_name(OUTPUT.name + ".partial")
    partial.mkdir(parents=True)
    sources = (
        (SOURCE / "m237r1_accept_fixed_text.py", "m237r1_accept_fixed_text.py"),
        (SOURCE / "m237r1_verify_measurement.py", "m237r1_verify_measurement.py"),
        (SOURCE / "run_m237r1_acceptance_repair.sh", "run_m237r1_acceptance_repair.sh"),
        (M230_VERIFY, "m230_verify_package.py"),
    )
    for source, name in sources:
        shutil.copy2(source, partial / name)
    (partial / "EXPECTED_M237_FIXED_TEXT_MEASUREMENT.json").write_text(
        json.dumps(fixed, indent=2) + "\n"
    )
    records = [
        {"path": path.name, "bytes": path.stat().st_size, "sha256": sha(path)}
        for path in sorted(partial.iterdir())
    ]
    manifest = {
        "date": "2026-09-01",
        "gate": "M237R1-acceptance-only-repair-delta",
        "status": "PASS",
        "classification": (
            "Hash-locked acceptance repair and immutable M237 measurement only; "
            "no bitstream, weights, runtime, model math, boot, DTB, CMA, partition, "
            "or service mutation."
        ),
        "m237_formal_result_sha256": sha(M237_RESULT),
        "files": records,
        "file_count": len(records),
        "total_file_bytes": sum(record["bytes"] for record in records),
        "forbidden_cache_file_count": 0,
        "board_state_changed": False,
    }
    (partial / "PACKAGE_MANIFEST.json").write_text(json.dumps(manifest, indent=2) + "\n")
    partial.replace(OUTPUT)
    result = {
        "date": "2026-09-01",
        "gate": "M237R1-acceptance-repair-delta-build",
        "status": "PASS",
        "directory": OUTPUT.relative_to(ROOT).as_posix(),
        "package_manifest_sha256": sha(OUTPUT / "PACKAGE_MANIFEST.json"),
        "file_count": len(records),
        "total_file_bytes": manifest["total_file_bytes"],
        "m237_formal_result_sha256": sha(M237_RESULT),
        "board_state_changed": False,
        "next_gate": "COM3 acceptance-only rerun against immutable M237 board measurement.",
    }
    BUILD_RESULT.write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps(result, indent=2))
    print("M237R1_ACCEPTANCE_REPAIR_DELTA_BUILD_PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
