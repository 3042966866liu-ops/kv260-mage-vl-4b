#!/usr/bin/env python3
"""Atomically apply the M175 host-runtime fix to a new board candidate."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
from pathlib import Path


EXPECTED_SOURCE_MANIFEST = "34662ca90cb45b9a1d34903538b030f28b1f9f70ece3f35e7ccbbaf6eb3bbf97"
EXPECTED_TARGET_MANIFEST = "406dcca340e4604baeb761445795391c43ec26bd99fa06ffae893d597b17414f"
CHANGED = {"SOURCE_MANIFEST.json", "runtime/board_runtime.py", "runtime/text_e2e_gate.py"}


def digest(path: Path) -> str:
    value = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(8 << 20), b""):
            value.update(block)
    return value.hexdigest()


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
        "gate": "M176-M120-LMHead-optional-layer-board-stage",
        "status": "FAIL",
        "classification": "Atomic host-runtime package correction only; not fixed-text E2E, full-model, performance, video or Web evidence.",
        "candidate_build_id": "0x4D395832",
    }
    staging: Path | None = None
    try:
        if os.geteuid() != 0:
            raise RuntimeError("M176 requires root")
        parent = Path("/home/ubuntu/tellme_m120_m89x2_20260901").resolve()
        delta, source, output = args.delta_root.resolve(), args.source.resolve(), args.output.resolve()
        if delta != parent / "m176_delta_01" or source != parent / "m165_m120_layer0_board_candidate" or output != parent / "m175_m120_fixed_text_candidate":
            raise RuntimeError("M176 fixed path identity mismatch")
        staging = output.with_name(output.name + ".staging")
        if output.exists() or staging.exists():
            raise RuntimeError("M176 requires absent output and staging")
        manifest_path = delta / "DELTA_MANIFEST.json"
        if digest(manifest_path) != args.expected_delta_manifest_sha256:
            raise RuntimeError("M176 delta manifest hash mismatch")
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        entries = manifest.get("files")
        if manifest.get("status") != "PASS" or not isinstance(entries, list) or len(entries) != 5:
            raise RuntimeError("M176 delta manifest identity mismatch")
        expected_delta = {"DELTA_MANIFEST.json", *(item["path"] for item in entries)}
        actual_delta = {path.relative_to(delta).as_posix() for path in delta.rglob("*") if path.is_file()}
        if actual_delta != expected_delta:
            raise RuntimeError("M176 delta closure mismatch")
        for item in entries:
            path = delta / item["path"]
            if path.is_symlink() or path.stat().st_size != int(item["bytes"]) or digest(path) != item["sha256"]:
                raise RuntimeError(f"M176 delta member mismatch: {item['path']}")
        if digest(source / "PACKAGE_MANIFEST.json") != EXPECTED_SOURCE_MANIFEST:
            raise RuntimeError("M176 source package identity mismatch")
        if digest(delta / "PACKAGE_MANIFEST.json") != EXPECTED_TARGET_MANIFEST:
            raise RuntimeError("M176 target package identity mismatch")

        shutil.copytree(source, staging)
        for relative in CHANGED:
            shutil.copyfile(delta / relative, staging / relative)
        shutil.copyfile(delta / "PACKAGE_MANIFEST.json", staging / "PACKAGE_MANIFEST.json")
        target = json.loads((staging / "PACKAGE_MANIFEST.json").read_text(encoding="utf-8"))
        expected_paths = {item["path"] for item in target["files"]}
        actual_paths = {path.relative_to(staging).as_posix() for path in staging.rglob("*") if path.is_file() and path.name != "PACKAGE_MANIFEST.json"}
        if expected_paths != actual_paths or len(expected_paths) != 18:
            raise RuntimeError("M176 target closure mismatch")
        for item in target["files"]:
            path = staging / item["path"]
            if path.stat().st_size != int(item["bytes"]) or digest(path) != item["sha256"]:
                raise RuntimeError(f"M176 target member mismatch: {item['path']}")
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
            "next_gate": "Rerun only M168 fixed-text E2E against this corrected candidate.",
        })
    except BaseException as error:
        if staging is not None and staging.exists():
            shutil.rmtree(staging)
        result["error"] = f"{type(error).__name__}: {error}"
        result["next_gate"] = "Repair and rerun M176 stage only; do not rerun fixed-text E2E."
    atomic_json(args.result, result)
    print("__M176_STAGE_RESULT_BEGIN__", flush=True)
    print(json.dumps(result, separators=(",", ":")), flush=True)
    print("__M176_STAGE_RESULT_END__", flush=True)
    print("M176_LMHEAD_OPTIONAL_LAYER_STAGE_PASS" if result["status"] == "PASS" else "M176_LMHEAD_OPTIONAL_LAYER_STAGE_FAIL", flush=True)
    return 0 if result["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
