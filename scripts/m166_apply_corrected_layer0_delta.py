#!/usr/bin/env python3
"""Apply the three-file M165 auxiliary correction to a new board directory."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
from pathlib import Path


EXPECTED_SOURCE_MANIFEST = "732b881d3507eaa12b8488e9224835ac115b686a003c748c9fa05a9793041d13"
EXPECTED_TARGET_MANIFEST = "34662ca90cb45b9a1d34903538b030f28b1f9f70ece3f35e7ccbbaf6eb3bbf97"
CHANGED = {
    "SOURCE_MANIFEST.json",
    "auxiliary/M77_TEXT_AUX_MANIFEST.json",
    "auxiliary/m77_text_aux_fp16.npz",
}


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(8 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def atomic_json(path: Path, value: dict) -> None:
    temporary = path.with_name(path.name + f".partial-{os.getpid()}")
    temporary.write_text(json.dumps(value, indent=2) + "\n", encoding="utf-8")
    os.replace(temporary, path)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--delta-root", type=Path, required=True)
    parser.add_argument("--expected-delta-manifest-sha256", required=True)
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--result", type=Path, required=True)
    args = parser.parse_args()
    result = {
        "date": "2026-09-01",
        "gate": "M166-M120-corrected-Layer0-board-stage",
        "status": "FAIL",
        "classification": "Atomic board package correction only; not Layer-0, fixed-text, full-model, performance, video or Web evidence.",
        "candidate_build_id": "0x4D395832",
    }
    staging: Path | None = None
    try:
        if os.geteuid() != 0:
            raise RuntimeError("M166 requires root")
        allowed_parent = Path("/home/ubuntu/tellme_m120_m89x2_20260901").resolve()
        delta = args.delta_root.resolve()
        source = args.source.resolve()
        output = args.output.resolve()
        if delta != allowed_parent / "m166_delta_01" or source != allowed_parent / "m120_text4b_layer0_board_candidate" or output != allowed_parent / "m165_m120_layer0_board_candidate":
            raise RuntimeError("M166 fixed path identity mismatch")
        staging = output.with_name(output.name + ".staging")
        if output.exists() or staging.exists():
            raise RuntimeError("M166 requires absent output and staging")
        delta_manifest_path = delta / "DELTA_MANIFEST.json"
        if sha256(delta_manifest_path) != args.expected_delta_manifest_sha256:
            raise RuntimeError("M166 delta manifest hash mismatch")
        delta_manifest = json.loads(delta_manifest_path.read_text(encoding="utf-8"))
        entries = delta_manifest.get("files")
        if delta_manifest.get("status") != "PASS" or not isinstance(entries, list) or len(entries) != 5:
            raise RuntimeError("M166 delta manifest identity mismatch")
        expected_delta = {"DELTA_MANIFEST.json", *(item["path"] for item in entries)}
        actual_delta = {path.relative_to(delta).as_posix() for path in delta.rglob("*") if path.is_file()}
        if actual_delta != expected_delta:
            raise RuntimeError("M166 delta closure mismatch")
        for item in entries:
            path = delta / item["path"]
            if path.is_symlink() or path.stat().st_size != int(item["bytes"]) or sha256(path) != item["sha256"]:
                raise RuntimeError(f"M166 delta member mismatch: {item['path']}")
        if sha256(source / "PACKAGE_MANIFEST.json") != EXPECTED_SOURCE_MANIFEST:
            raise RuntimeError("M166 source package identity mismatch")
        if sha256(delta / "PACKAGE_MANIFEST.json") != EXPECTED_TARGET_MANIFEST:
            raise RuntimeError("M166 target manifest identity mismatch")

        shutil.copytree(source, staging)
        for relative in CHANGED:
            shutil.copyfile(delta / relative, staging / relative)
        shutil.copyfile(delta / "PACKAGE_MANIFEST.json", staging / "PACKAGE_MANIFEST.json")
        target_manifest = json.loads((staging / "PACKAGE_MANIFEST.json").read_text(encoding="utf-8"))
        expected_paths = {item["path"] for item in target_manifest["files"]}
        actual_paths = {path.relative_to(staging).as_posix() for path in staging.rglob("*") if path.is_file() and path.name != "PACKAGE_MANIFEST.json"}
        if expected_paths != actual_paths or len(expected_paths) != 18:
            raise RuntimeError("M166 target closure mismatch")
        for item in target_manifest["files"]:
            path = staging / item["path"]
            if path.stat().st_size != int(item["bytes"]) or sha256(path) != item["sha256"]:
                raise RuntimeError(f"M166 target member mismatch: {item['path']}")
        os.replace(staging, output)
        staging = None
        result.update({
            "status": "PASS",
            "source_package_manifest_sha256": EXPECTED_SOURCE_MANIFEST,
            "package_manifest_sha256": EXPECTED_TARGET_MANIFEST,
            "output": str(output),
            "file_count": 18,
            "changed_files": sorted(CHANGED),
            "boot_dtb_cma_partitions_services_changed": False,
            "stable_rollback_preserved": True,
            "next_gate": "Rerun only M144 complete Layer-0 against this corrected candidate.",
        })
    except BaseException as error:
        if staging is not None and staging.exists():
            shutil.rmtree(staging)
        result["error"] = f"{type(error).__name__}: {error}"
        result["next_gate"] = "Repair and rerun M166 stage only; do not execute Layer-0."
    atomic_json(args.result, result)
    print("__M166_STAGE_RESULT_BEGIN__", flush=True)
    print(json.dumps(result, separators=(",", ":")), flush=True)
    print("__M166_STAGE_RESULT_END__", flush=True)
    print("M166_CORRECTED_LAYER0_STAGE_PASS" if result["status"] == "PASS" else "M166_CORRECTED_LAYER0_STAGE_FAIL", flush=True)
    return 0 if result["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
