#!/usr/bin/env python3
"""Build the clean M294 27-measurement KV260 package."""

from __future__ import annotations

import hashlib
import json
import os
import shutil
import tarfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DEPLOYMENT = ROOT / "deployment/mage_vl4b"
BASE = DEPLOYMENT / "m283_bact_boundary_board_candidate"
SOURCE = DEPLOYMENT / "m294_counterbalanced_boundary_source"
OUTER_SOURCE = DEPLOYMENT / "m284_bact_outer_boundaries_source/m284_outer_boundary_contract.py"
DEST = DEPLOYMENT / "m294_counterbalanced_boundary_board_candidate"
PARTIAL = DEST.with_name(DEST.name + ".partial")
ARCHIVE = DEPLOYMENT / "m294_counterbalanced_boundary_board_candidate.tar.gz"
BUILD_RESULT = DEPLOYMENT / "M294_COUNTERBALANCED_BOUNDARY_BUILD_RESULT.json"
BASE_MANIFEST_SHA256 = "d81aaf27d0b817e59edf79a0b1426fe9ea44b3ee45331876cb8677f1c9765144"
EXCLUDE_BASE = {
    "PACKAGE_MANIFEST.json",
    "m283_bact_boundary_gate.py",
    "m283_stage_archive.py",
    "m283_verify_package.py",
    "run_m283_bact_boundary_gate.sh",
}
EVIDENCE = (
    DEPLOYMENT / "M281_BACT_159_160_161_GEOMETRY_RESULT.json",
    DEPLOYMENT / "M284_BACT_OUTER_BOUNDARY_GEOMETRY_RESULT.json",
    DEPLOYMENT / "M293_COUNTERBALANCED_BOUNDARY_PLAN_RESULT.json",
)


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> int:
    outputs = (DEST, PARTIAL, ARCHIVE, BUILD_RESULT)
    if any(path.exists() for path in outputs):
        raise RuntimeError("M294 output already exists; refuse overwrite")
    base_manifest = BASE / "PACKAGE_MANIFEST.json"
    observed_base_hash = sha256(base_manifest)
    if observed_base_hash != BASE_MANIFEST_SHA256:
        raise RuntimeError(
            f"M294 M283 base manifest hash mismatch observed={observed_base_hash}"
        )
    sources = {
        path.name: path
        for path in BASE.iterdir()
        if path.is_file() and path.name not in EXCLUDE_BASE
    }
    for path in SOURCE.iterdir():
        if path.is_file():
            sources[path.name] = path
    sources[OUTER_SOURCE.name] = OUTER_SOURCE
    for path in EVIDENCE:
        sources[path.name] = path
    PARTIAL.mkdir(parents=False)
    try:
        files = []
        for name, source in sorted(sources.items()):
            if not source.is_file():
                raise RuntimeError(f"M294 missing source {source}")
            destination = PARTIAL / name
            shutil.copy2(source, destination)
            files.append({
                "path": name,
                "bytes": destination.stat().st_size,
                "sha256": sha256(destination),
            })
        plan = json.loads(
            (DEPLOYMENT / "M293_COUNTERBALANCED_BOUNDARY_PLAN_RESULT.json").read_text(
                encoding="utf-8"
            )
        )
        schedule = plan["schedule"]
        expected_measured_calls = sum(
            int(item["expected_logical_fpga_calls"]) for item in schedule
        )
        warmup_calls = 778
        manifest = {
            "schema": "tellme-m294-counterbalanced-boundary-v1",
            "status": "PASS_OFFLINE_READY_FOR_M294_BOARD_GATE",
            "classification": (
                "Hash-locked one-load/one-vision, 27-measurement counterbalanced "
                "KV260 boundary pilot package; not yet board-executed or performance-promoted."
            ),
            "predecessor_m283_manifest_sha256": observed_base_hash,
            "files": files,
            "file_count": len(files),
            "total_bytes": sum(item["bytes"] for item in files),
            "build_id": "0x4D395832",
            "kernel": "mage_m120_m89x2_0",
            "boundary_triplets": [[127, 128, 129], [159, 160, 161], [191, 192, 193]],
            "expected_measurement_count": 27,
            "expected_measured_logical_calls": expected_measured_calls,
            "unmeasured_warmup_tokens": 159,
            "unmeasured_warmup_logical_calls": warmup_calls,
            "expected_total_logical_calls_including_warmup": expected_measured_calls + warmup_calls,
            "runtime_load_count": 1,
            "vision_execution_count": 1,
            "partial_progress_checkpoint": True,
            "resume_after_process_restart_allowed": False,
            "new_hls_or_rtl": False,
            "kernel_math_changed": False,
            "stable_restore_attempts": 2,
            "stable_rollback_preserved": True,
            "excluded": ["__pycache__", "*.pyc", "temporary logs", "superseded M283 runner"],
        }
        (PARTIAL / "PACKAGE_MANIFEST.json").write_text(
            json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8"
        )
        os.replace(PARTIAL, DEST)
        with tarfile.open(ARCHIVE, "w:gz", compresslevel=9) as archive:
            for path in sorted(DEST.iterdir()):
                archive.add(path, arcname=path.name, recursive=False)
        result = {
            "date": "2026-09-02",
            "gate": "M294-counterbalanced-boundary-clean-package",
            "status": "M294_BUILD_PASS",
            "classification": (
                "Clean hash-locked 27-measurement board package only; no new board, "
                "TTFT distribution, semantic accuracy or speed claim."
            ),
            "directory": str(DEST.relative_to(ROOT)).replace("\\", "/"),
            "manifest_sha256": sha256(DEST / "PACKAGE_MANIFEST.json"),
            "file_count": manifest["file_count"],
            "total_bytes": manifest["total_bytes"],
            "archive": str(ARCHIVE.relative_to(ROOT)).replace("\\", "/"),
            "archive_bytes": ARCHIVE.stat().st_size,
            "archive_sha256": sha256(ARCHIVE),
            "expected_measurement_count": 27,
            "expected_measured_logical_calls": expected_measured_calls,
            "expected_total_logical_calls_including_warmup": expected_measured_calls + warmup_calls,
            "board_execution_run": False,
            "active_board_service_changed": False,
            "boot_dtb_cma_partitions_changed": False,
            "stable_rollback_preserved": True,
            "source_sha256": sha256(Path(__file__).resolve()),
            "next_gate": (
                "Run Windows AST/hash/cache, PowerShell 7 parser, explicit Ubuntu-24.04 "
                "runtime import and Bash syntax closure before any COM3 action."
            ),
        }
        partial_result = BUILD_RESULT.with_name(BUILD_RESULT.name + f".partial-{os.getpid()}")
        partial_result.write_text(
            json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8"
        )
        os.replace(partial_result, BUILD_RESULT)
    except Exception:
        if PARTIAL.exists():
            shutil.rmtree(PARTIAL)
        if DEST.exists():
            shutil.rmtree(DEST)
        if ARCHIVE.exists():
            ARCHIVE.unlink()
        raise
    print(
        f"M294_BUILD_PASS files={result['file_count']} bytes={result['total_bytes']} "
        f"manifest={result['manifest_sha256']} archive={result['archive_sha256']}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
