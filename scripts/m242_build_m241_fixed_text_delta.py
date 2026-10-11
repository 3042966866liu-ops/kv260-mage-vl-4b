#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import json
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "deployment/mage_vl4b/m242_m241_fixed_text_source"
M241 = ROOT / "deployment/mage_vl4b/m241_grouped_gqa_board_candidate"
FORMAL = ROOT / "deployment/mage_vl4b/M241_GROUPED_GQA_BOARD_RESULT_01.json"
OUTPUT = ROOT / "deployment/mage_vl4b/m242_m241_fixed_text_board_candidate"
RESULT = ROOT / "deployment/mage_vl4b/M242_M241_FIXED_TEXT_BOARD_DELTA_RESULT.json"


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def canonical_sha(value: object) -> str:
    payload = json.dumps(value, sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(payload).hexdigest()


def main() -> int:
    if OUTPUT.exists() or OUTPUT.with_name(OUTPUT.name + ".partial").exists():
        raise RuntimeError("M242 clean output required")
    formal = json.loads(FORMAL.read_text(encoding="utf-8"))
    prefill = formal.get("prefill_gate", {})
    if formal.get("status") != "PASS_SERVICE_RESTORED" or prefill.get("status") != "PASS":
        raise RuntimeError("M242 requires the exact M241 board PASS")
    predecessor = {
        "date": "2026-09-01",
        "gate": "M242-M241-exact-board-predecessor",
        "status": "PASS",
        "m241_formal_result_sha256": sha(FORMAL),
        "prefill_gate_canonical_sha256": canonical_sha(prefill),
        "build_id": "0x4D395832",
        "tokens": 849,
        "generated_token_id": 40183,
    }
    partial = OUTPUT.with_name(OUTPUT.name + ".partial")
    partial.mkdir(parents=True)
    names = [
        "m230_verify_package.py", "m230_prefill_runtime.py", "m231_prefill_runtime.py",
        "m236_prefill_runtime.py", "m238_prefill_runtime.py", "m230_video_language_runtime.py",
        "m241_video_language_runtime.py",
    ]
    for name in names:
        shutil.copy2(M241 / name, partial / name)
    for name in ["m242_fixed_text_gate.py", "m242_verify_predecessor.py", "m242_accept_fixed_text.py", "run_m242_fixed_text_gate.sh"]:
        shutil.copy2(SOURCE / name, partial / name)
    (partial / "M241_PREDECESSOR_SUMMARY.json").write_text(json.dumps(predecessor, indent=2) + "\n", encoding="utf-8")
    records = [{"path": p.name, "bytes": p.stat().st_size, "sha256": sha(p)} for p in sorted(partial.iterdir())]
    manifest = {
        "date": "2026-09-01", "gate": "M242-M241-fixed-text-runtime-board-delta", "status": "PASS",
        "classification": "Clean runtime-only M241 fixed-text delta; no bitstream, weights, quantization, boot, DTB, CMA, partition, or persistent service mutation.",
        "base_build_id": "0x4D395832",
        "base_package_manifest_sha256": "406dcca340e4604baeb761445795391c43ec26bd99fa06ffae893d597b17414f",
        "files": records, "file_count": len(records), "total_file_bytes": sum(x["bytes"] for x in records),
        "forbidden_cache_file_count": 0, "board_state_changed": False,
    }
    (partial / "PACKAGE_MANIFEST.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    partial.replace(OUTPUT)
    result = {
        "date": "2026-09-01", "gate": "M242-M241-fixed-text-board-delta-build", "status": "PASS",
        "directory": OUTPUT.relative_to(ROOT).as_posix(), "package_manifest_sha256": sha(OUTPUT / "PACKAGE_MANIFEST.json"),
        "file_count": len(records), "total_file_bytes": manifest["total_file_bytes"], "board_state_changed": False,
        "next_gate": "COM3 exact M241 predecessor plus frozen fixed-text complete 4B E2E.",
    }
    RESULT.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, indent=2))
    print("M242_M241_FIXED_TEXT_DELTA_BUILD_PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
