#!/usr/bin/env python3
"""Build a clean M165 Layer-0 package with the corrected M120 W3 prompt rows."""

from __future__ import annotations

import hashlib
import json
import os
import shutil
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "deployment/mage_vl4b/m120_text4b_layer0_board_candidate"
OUTPUT = ROOT / "deployment/mage_vl4b/m165_m120_layer0_board_candidate"
AUX = ROOT / "deployment/mage_vl4b/artifacts/m165_m120_selected_w3_aux_fp16.npz"
AUX_MANIFEST_SOURCE = ROOT / "deployment/mage_vl4b/artifacts/M165_M120_SELECTED_W3_AUX_MANIFEST.json"
AUX_RESULT = ROOT / "deployment/mage_vl4b/M165_M120_SELECTED_W3_AUX_RESULT.json"
RESULT = ROOT / "deployment/mage_vl4b/M165_M120_CORRECTED_LAYER0_PACKAGE_RESULT.json"
EXPECTED_OLD_PACKAGE = "732b881d3507eaa12b8488e9224835ac115b686a003c748c9fa05a9793041d13"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(16 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def atomic_json(path: Path, value: dict) -> None:
    temporary = path.with_name(path.name + f".partial-{os.getpid()}")
    temporary.write_text(json.dumps(value, indent=2) + "\n", encoding="utf-8")
    os.replace(temporary, path)


def main() -> int:
    result = {
        "date": "2026-09-01",
        "gate": "M165-M120-corrected-Layer0-package",
        "status": "FAIL",
        "classification": "Offline clean package correction only; not board, Layer-0, fixed-text, performance, video or Web evidence.",
        "board_state_changed": False,
        "stable_rollback_preserved": True,
    }
    staging = OUTPUT.with_name(OUTPUT.name + f".partial-{os.getpid()}")
    try:
        if OUTPUT.exists() or staging.exists():
            raise RuntimeError("M165 clean package output required")
        if sha256(SOURCE / "PACKAGE_MANIFEST.json") != EXPECTED_OLD_PACKAGE:
            raise RuntimeError("M165 old M145 package identity drift")
        aux_result = json.loads(AUX_RESULT.read_text(encoding="utf-8"))
        if aux_result.get("status") != "PASS" or sha256(AUX) != aux_result.get("auxiliary_sha256"):
            raise RuntimeError("M165 corrected auxiliary prerequisite mismatch")
        if sha256(AUX_MANIFEST_SOURCE) != aux_result.get("auxiliary_manifest_sha256"):
            raise RuntimeError("M165 corrected auxiliary manifest mismatch")

        shutil.copytree(SOURCE, staging)
        target_aux = staging / "auxiliary/m77_text_aux_fp16.npz"
        shutil.copyfile(AUX, target_aux)
        board_aux_manifest = json.loads(AUX_MANIFEST_SOURCE.read_text(encoding="utf-8"))
        board_aux_manifest["payload"] = "m77_text_aux_fp16.npz"
        board_aux_manifest["payload_bytes"] = target_aux.stat().st_size
        board_aux_manifest["payload_sha256"] = sha256(target_aux)
        board_aux_manifest["source_m165_auxiliary_manifest_sha256"] = sha256(AUX_MANIFEST_SOURCE)
        atomic_json(staging / "auxiliary/M77_TEXT_AUX_MANIFEST.json", board_aux_manifest)

        source_manifest_path = staging / "SOURCE_MANIFEST.json"
        source_manifest = json.loads(source_manifest_path.read_text(encoding="utf-8"))
        source_manifest.update({
            "gate": "M165-M120-corrected-full-text-runtime-source",
            "status": "SOURCE_CORRECTED_NOT_BOARD_EXECUTED",
            "embedding_policy": "M120 W3-G64 selected fixed-prompt rows",
            "m165_auxiliary_result_sha256": sha256(AUX_RESULT),
        })
        by_path = {item["path"]: item for item in source_manifest["files"]}
        for relative, origin in (
            ("auxiliary/m77_text_aux_fp16.npz", "M165 exact M120 W3-G64 selected rows"),
            ("auxiliary/M77_TEXT_AUX_MANIFEST.json", "M165 corrected fixed-text auxiliary manifest"),
        ):
            path = staging / relative
            by_path[relative].update({"bytes": path.stat().st_size, "sha256": sha256(path), "source": origin})
        atomic_json(source_manifest_path, source_manifest)

        old_package = json.loads((staging / "PACKAGE_MANIFEST.json").read_text(encoding="utf-8"))
        old_paths = {item["path"] for item in old_package["files"]}
        actual_paths = {
            path.relative_to(staging).as_posix()
            for path in staging.rglob("*")
            if path.is_file() and path.name != "PACKAGE_MANIFEST.json"
        }
        if old_paths != actual_paths or any("__pycache__" in path or path.endswith(".pyc") for path in actual_paths):
            raise RuntimeError("M165 inherited package closure mismatch")
        entries = []
        for relative in sorted(actual_paths):
            path = staging / relative
            entries.append({"path": relative, "bytes": path.stat().st_size, "sha256": sha256(path)})
        package = {
            **{key: value for key, value in old_package.items() if key != "files"},
            "gate": "M165-M120-corrected-layer0-board-package",
            "status": "OFFLINE_PACKAGE_PASS_BOARD_NOT_EXECUTED",
            "source_manifest_sha256": sha256(source_manifest_path),
            "m165_auxiliary_result_sha256": sha256(AUX_RESULT),
            "embedding_policy": "M120 W3-G64 selected fixed-prompt rows",
            "files": entries,
            "board_state_changed": False,
            "stable_rollback_preserved": True,
        }
        atomic_json(staging / "PACKAGE_MANIFEST.json", package)
        os.replace(staging, OUTPUT)
        result.update({
            "status": "PASS",
            "candidate": OUTPUT.relative_to(ROOT).as_posix(),
            "package_manifest_sha256": sha256(OUTPUT / "PACKAGE_MANIFEST.json"),
            "file_count": len(entries),
            "total_bytes": sum(item["bytes"] for item in entries),
            "source_manifest_sha256": sha256(OUTPUT / "SOURCE_MANIFEST.json"),
            "auxiliary_sha256": sha256(OUTPUT / "auxiliary/m77_text_aux_fp16.npz"),
            "auxiliary_manifest_sha256": sha256(OUTPUT / "auxiliary/M77_TEXT_AUX_MANIFEST.json"),
            "next_gate": "Stage a delta-derived new board directory and rerun only M144 Layer-0.",
        })
    except BaseException as error:
        if staging.exists():
            shutil.rmtree(staging)
        result["error"] = f"{type(error).__name__}: {error}"
        result["next_gate"] = "Repair and rerun M165 package build offline only."
    RESULT.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, indent=2))
    print("M165_CORRECTED_LAYER0_PACKAGE_PASS" if result["status"] == "PASS" else "M165_CORRECTED_LAYER0_PACKAGE_FAIL")
    return 0 if result["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
