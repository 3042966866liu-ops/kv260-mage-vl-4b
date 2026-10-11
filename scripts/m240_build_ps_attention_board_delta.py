#!/usr/bin/env python3
"""Build a clean, hash-closed M240 PS-attention micro-gate package."""
from __future__ import annotations

import hashlib
import json
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "deployment/mage_vl4b/m240_ps_attention_source"
VERIFY = ROOT / "deployment/mage_vl4b/m230_prefill_stage_once_source/m230_verify_package.py"
OUTPUT = ROOT / "deployment/mage_vl4b/m240_ps_attention_board_candidate"
PREDECESSOR = ROOT / "deployment/mage_vl4b/M239_FULL849_PROFILE_BOARD_RESULT_02.json"
RESULT = ROOT / "deployment/mage_vl4b/M240_PS_ATTENTION_BOARD_DELTA_RESULT.json"
FILES = (
    (SOURCE / "m240_attention_board_gate.py", "m240_attention_board_gate.py"),
    (SOURCE / "run_m240_board_gate.sh", "run_m240_board_gate.sh"),
    (VERIFY, "m230_verify_package.py"),
)


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> int:
    if OUTPUT.exists() or OUTPUT.with_name(OUTPUT.name + ".partial").exists():
        raise RuntimeError(f"M240 clean output required: {OUTPUT}")
    predecessor = json.loads(PREDECESSOR.read_text(encoding="utf-8"))
    if predecessor.get("status") != "MEASURED_SERVICE_RESTORED":
        raise RuntimeError("M239 predecessor mismatch")
    partial = OUTPUT.with_name(OUTPUT.name + ".partial")
    partial.mkdir(parents=True)
    records = []
    for source, relative in FILES:
        if not source.is_file():
            raise RuntimeError(f"M240 missing source: {source}")
        destination = partial / relative
        shutil.copy2(source, destination)
        records.append({"path": relative, "bytes": destination.stat().st_size, "sha256": sha(destination)})
    forbidden = [
        path.relative_to(partial).as_posix()
        for path in partial.rglob("*")
        if path.is_file() and (path.suffix == ".pyc" or "__pycache__" in path.parts)
    ]
    if forbidden:
        raise RuntimeError(f"M240 forbidden files: {forbidden}")
    manifest = {
        "date": "2026-09-01",
        "gate": "M240-PS-attention-board-micro-gate-delta",
        "status": "PASS",
        "classification": "PS-only numerical/performance micro-gate; no overlay, bitstream, model weight, FPGA transaction, boot, DTB, CMA, partition, or persistent-service mutation.",
        "m239_predecessor_sha256": sha(PREDECESSOR),
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
        "gate": "M240-PS-attention-board-micro-gate-delta-build",
        "status": "PASS",
        "directory": OUTPUT.relative_to(ROOT).as_posix(),
        "package_manifest_sha256": sha(OUTPUT / "PACKAGE_MANIFEST.json"),
        "file_count": len(records),
        "total_file_bytes": manifest["total_file_bytes"],
        "board_state_changed": False,
        "next_gate": "COM3 real-KV260 849-token PS attention micro-gate; require FP32 bit-exact output and at least 1.05x median speedup, then exact service restoration.",
    }
    partial_result = RESULT.with_name(RESULT.name + ".partial")
    partial_result.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    partial_result.replace(RESULT)
    print(json.dumps(result, indent=2))
    print("M240_PS_ATTENTION_BOARD_DELTA_BUILD_PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
