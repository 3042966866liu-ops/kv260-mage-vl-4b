#!/usr/bin/env python3
"""Build exact, reverse-verified M120 language and LM-head four-port layouts."""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import os
import shutil
import sys
from pathlib import Path


EXPECTED_MANIFEST_SHA256 = "5ff33d1922376e18277902a8b051d069315f79c11b4f63e8d72517acd1dcd5d0"
EXPECTED_BLOB_SHA256 = "9c7de8995a08602186c7090081bbfc10b7c51170ad7e544f2f2dc71333b4f21d"
EXPECTED_LANGUAGE_BYTES = 1_828_839_424
EXPECTED_HEAD_BYTES = 206_632_960


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(16 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def load_layout_module() -> object:
    script = (
        Path(__file__).resolve().parents[1]
        / "deployment"
        / "mage_vl4b"
        / "scripts"
        / "sixport_runtime_layout.py"
    )
    spec = importlib.util.spec_from_file_location("m125_runtime_layout", script)
    if spec is None or spec.loader is None:
        raise RuntimeError("M125_LAYOUT_MODULE_LOAD_FAIL")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    module.SHARD_COUNT = 4
    module.FORMAT = "tellme-mage-vl-fourport-group-major-v1"
    return module


def atomic_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + f".tmp-{os.getpid()}")
    temporary.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    os.replace(temporary, path)


def finalize_manifest(layout_module: object, source: Path, output: Path, build_id: str) -> dict:
    manifest_path = output / "SIXPORT_LAYOUT_MANIFEST.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["build_id"] = build_id
    manifest["classification"] = (
        "exact M120 source-value byte-order transform; no requantization; "
        "reverse-verified against the frozen checkpoint"
    )
    manifest["source"].pop("fresh_process_accuracy_gate", None)
    manifest["source"].update(
        {
            "software_quality_gate": "M123_PASS",
            "software_quality_evidence": "M123_MIXED_PRECISION_SOFTWARE_QUALITY_DECISION.json",
        }
    )
    manifest_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    verification = layout_module.verify_layout(source, output, verify_source_blob=False)
    if verification["status"] != "PASS_EXACT_SOURCE_VALUES_AND_ZERO_PADDING":
        raise RuntimeError("M125_FINAL_REVERSE_VERIFICATION_FAIL")
    manifest["verification"] = verification
    manifest_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    return manifest


def summarize(output: Path, manifest: dict, expected_modules: int, expected_bytes: int) -> dict:
    files = []
    for item in manifest["files"]:
        path = output / item["path"]
        observed = {
            "path": item["path"],
            "bytes": path.stat().st_size,
            "sha256": sha256_file(path),
        }
        if observed["bytes"] != int(item["bytes"]) or observed["sha256"] != item["sha256"]:
            raise RuntimeError(f"M125_FILE_IDENTITY_FAIL path={path}")
        files.append(observed)
    mapped = sum(item["bytes"] for item in files)
    if len(manifest["modules"]) != expected_modules or mapped != expected_bytes:
        raise RuntimeError(
            f"M125_CARDINALITY_OR_SIZE_FAIL modules={len(manifest['modules'])} bytes={mapped}"
        )
    return {
        "directory": str(output),
        "manifest_sha256": sha256_file(output / "SIXPORT_LAYOUT_MANIFEST.json"),
        "module_count": len(manifest["modules"]),
        "tile_descriptor_count": sum(len(module["tiles"]) for module in manifest["modules"]),
        "mapped_bytes": mapped,
        "files": files,
        "verification": manifest["verification"],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--output-root", type=Path, required=True)
    parser.add_argument("--result", type=Path, required=True)
    args = parser.parse_args()

    result: dict[str, object] = {
        "date": "2026-08-31",
        "gate": "M125-exact-M120-fourport-layout-build",
        "status": "FAIL",
        "classification": "offline byte-layout build and exhaustive reverse verification only; not CSim, CoSim, FPGA, board, performance or Web evidence",
    }
    try:
        source = args.source.resolve()
        output_root = args.output_root.resolve()
        language_output = output_root / "language_fourport"
        head_output = output_root / "lmhead_fourport"
        if output_root.exists():
            raise FileExistsError(f"M125_REFUSE_OVERWRITE output={output_root}")
        manifest_path = source / "CHECKPOINT_MANIFEST.json"
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        if sha256_file(manifest_path) != EXPECTED_MANIFEST_SHA256:
            raise RuntimeError("M125_SOURCE_MANIFEST_IDENTITY_FAIL")
        if manifest["blob"]["sha256"] != EXPECTED_BLOB_SHA256:
            raise RuntimeError("M125_SOURCE_BLOB_DECLARATION_FAIL")
        if sha256_file(source / manifest["blob"]["path"]) != EXPECTED_BLOB_SHA256:
            raise RuntimeError("M125_SOURCE_BLOB_IDENTITY_FAIL")

        output_root.mkdir(parents=True)
        layout = load_layout_module()
        language_manifest = layout.build_layout(
            source,
            language_output,
            module_pattern=r"^model\.language_model\.layers\.",
            verify_source_blob=False,
        )
        language_manifest = finalize_manifest(
            layout, source, language_output, "M125-M120-LANGUAGE-FOURPORT-20260831"
        )
        head_manifest = layout.build_layout(
            source,
            head_output,
            module_pattern=r"^lm_head$",
            verify_source_blob=False,
        )
        head_manifest = finalize_manifest(
            layout, source, head_output, "M125-M120-LMHEAD-W4-FOURPORT-20260831"
        )

        language_summary = summarize(
            language_output, language_manifest, 252, EXPECTED_LANGUAGE_BYTES
        )
        head_summary = summarize(head_output, head_manifest, 1, EXPECTED_HEAD_BYTES)
        result.update(
            {
                "status": "PASS_EXACT_M120_LANGUAGE_AND_HEAD_FOURPORT_LAYOUTS",
                "checkpoint_manifest_sha256": EXPECTED_MANIFEST_SHA256,
                "checkpoint_blob_sha256": EXPECTED_BLOB_SHA256,
                "language": language_summary,
                "lm_head": head_summary,
                "requantized": False,
                "board_state_changed": False,
                "stable_rollback_preserved": True,
                "next_gate": "Generate and independently audit the 154 homogeneous-bit language chains plus W4 LM-head descriptor contract and same-quantized fixtures.",
            }
        )
    except BaseException as error:
        result["error"] = f"{type(error).__name__}: {error}"
        result["next_gate"] = "Correct this same offline layout gate; do not touch the board."

    atomic_json(args.result, result)
    print(json.dumps(result, indent=2, ensure_ascii=False), flush=True)
    if result["status"] != "PASS_EXACT_M120_LANGUAGE_AND_HEAD_FOURPORT_LAYOUTS":
        return 1
    print("M125_EXACT_M120_FOURPORT_LAYOUTS_PASS", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
