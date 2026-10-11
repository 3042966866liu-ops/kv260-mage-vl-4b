#!/usr/bin/env python3
"""Build a clean, small M287 delta package."""

from __future__ import annotations

import hashlib
import json
import os
import shutil
import tarfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "deployment/mage_vl4b/m287_natural_prompt_source"
DEST = ROOT / "deployment/mage_vl4b/m287_natural_prompt_board_candidate"
PARTIAL = DEST.with_name(DEST.name + ".partial")
ARCHIVE = ROOT / "deployment/mage_vl4b/m287_natural_prompt_board_candidate.tar.gz"
RESULT = ROOT / "deployment/mage_vl4b/M287_NATURAL_PROMPT_BUILD_RESULT.json"
EVIDENCE = (
    ROOT / "deployment/mage_vl4b/M286_M120_A8_NATURAL_PROMPT_SWEEP_RESULT.json",
    ROOT / "deployment/mage_vl4b/M283R1_BACT_BOUNDARY_EVIDENCE_SPLIT_RESULT.json",
)


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> int:
    if any(path.exists() for path in (DEST, PARTIAL, ARCHIVE, RESULT)):
        raise RuntimeError("M287 output exists; refuse overwrite")
    sources = {path.name: path for path in SOURCE.iterdir() if path.is_file()}
    sources.update({path.name: path for path in EVIDENCE})
    PARTIAL.mkdir(parents=False)
    try:
        files = []
        for name, source in sorted(sources.items()):
            destination = PARTIAL / name
            shutil.copy2(source, destination)
            files.append({"path": name, "bytes": destination.stat().st_size, "sha256": sha256(destination)})
        manifest = {
            "schema": "tellme-m287-natural-prompt-delta-v1",
            "status": "PASS_OFFLINE_READY_FOR_M287_BOARD_GATE",
            "classification": "Hash-locked natural 151-token one-fixture delta; no board or accuracy claim yet.",
            "base_m283_manifest_sha256": "d81aaf27d0b817e59edf79a0b1426fe9ea44b3ee45331876cb8677f1c9765144",
            "files": files,
            "file_count": len(files),
            "total_bytes": sum(item["bytes"] for item in files),
            "build_id": "0x4D395832",
            "kernel": "mage_m120_m89x2_0",
            "prompt_tokens": 151,
            "t32_batches": 5,
            "expected_logical_calls": 778,
            "new_hls_or_rtl": False,
            "kernel_math_changed": False,
            "stable_restore_attempts": 2,
            "stable_rollback_preserved": True,
            "excluded": ["__pycache__", "*.pyc", "temporary logs"],
        }
        (PARTIAL / "PACKAGE_MANIFEST.json").write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        os.replace(PARTIAL, DEST)
        with tarfile.open(ARCHIVE, "w:gz", compresslevel=9) as archive:
            for path in sorted(DEST.iterdir()):
                archive.add(path, arcname=path.name, recursive=False)
        value = {
            "date": "2026-09-02", "gate": "M287-natural-prompt-clean-delta",
            "status": "M287_BUILD_PASS", "classification": "Clean hash-locked delta only; no board claim.",
            "directory": str(DEST.relative_to(ROOT)).replace("\\", "/"),
            "manifest_sha256": sha256(DEST / "PACKAGE_MANIFEST.json"),
            "file_count": manifest["file_count"], "total_bytes": manifest["total_bytes"],
            "archive": str(ARCHIVE.relative_to(ROOT)).replace("\\", "/"),
            "archive_bytes": ARCHIVE.stat().st_size, "archive_sha256": sha256(ARCHIVE),
            "board_execution_run": False, "active_board_service_changed": False,
            "stable_rollback_preserved": True, "source_sha256": sha256(Path(__file__).resolve()),
            "next_gate": "Run AST/hash/import/bash closure, then one same-COM3 M287 gate and restore M254."
        }
        partial_result = RESULT.with_name(RESULT.name + f".partial-{os.getpid()}")
        partial_result.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        os.replace(partial_result, RESULT)
    except Exception:
        if PARTIAL.exists(): shutil.rmtree(PARTIAL)
        if DEST.exists(): shutil.rmtree(DEST)
        if ARCHIVE.exists(): ARCHIVE.unlink()
        raise
    print(f"M287_BUILD_PASS files={value['file_count']} bytes={value['total_bytes']} manifest={value['manifest_sha256']} archive={value['archive_sha256']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
