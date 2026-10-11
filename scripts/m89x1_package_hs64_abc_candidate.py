#!/usr/bin/env python3
"""Create a clean HS64 A/B/C Layer-0 diagnostic candidate from the staged baseline."""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
from pathlib import Path


BASELINE_SHA256 = "8b45d93ac104006eff98acf9ce4479922c49dc0be7e225b201cfa0671a472679"
REPLACEMENTS = {
    "runtime/m89x1_qkv_reference_helper.py": "scripts/m89x1_qkv_reference_helper.py",
    "runtime/m89x1_layer0_tolerance_diagnostic.py": "scripts/m89x1_layer0_tolerance_diagnostic.py",
    "runtime/m89x1_layer0_acceptance_gate.py": "scripts/m89x1_layer0_acceptance_gate.py",
    "runtime/run_m89x1_hostscale64_layer0_gate.sh": "scripts/run_m89x1_hostscale64_layer0_gate.sh",
    "contracts/M89X1_HS64_HLS_HALF_REFERENCE_RESULT.json":
        "deployment/mage_vl4b/M89X1_HS64_HLS_HALF_REFERENCE_RESULT.json",
}


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(8 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--workspace", type=Path, required=True)
    parser.add_argument("--baseline", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    workspace, baseline, output = args.workspace.resolve(), args.baseline.resolve(), args.output.resolve()
    if output.exists():
        raise RuntimeError(f"output already exists: {output}")
    baseline_manifest_path = baseline / "PACKAGE_MANIFEST.json"
    if sha256(baseline_manifest_path) != BASELINE_SHA256:
        raise RuntimeError("HS64 staged baseline identity mismatch")
    baseline_manifest = json.loads(baseline_manifest_path.read_text(encoding="utf-8"))
    shutil.copytree(baseline, output, ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
    for relative, source_relative in REPLACEMENTS.items():
        destination = output / relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(workspace / source_relative, destination)

    files = []
    for path in sorted(output.rglob("*")):
        if not path.is_file() or path.name == "PACKAGE_MANIFEST.json":
            continue
        relative = path.relative_to(output).as_posix()
        if "__pycache__" in path.parts or path.suffix == ".pyc":
            raise RuntimeError(f"forbidden cache in candidate: {relative}")
        files.append({"path": relative, "bytes": path.stat().st_size, "sha256": sha256(path)})
    manifest = dict(baseline_manifest)
    manifest.update(
        build="M89-X1-HS64-ABC/Z2",
        status="PASS_OFFLINE_BOARD_ANCHORED_DIAGNOSTIC_CANDIDATE",
        marker="M89X1_HOST_SCALE64_ABC_CANDIDATE_PACKAGE_PASS",
        baseline_manifest_sha256=BASELINE_SHA256,
        deployed=False,
        board_state_changed=False,
        diagnostic_contract={
            "method": "A=reference(reference input), B=reference(observed input), C=FPGA(observed input)",
            "local_error": "C-B",
            "propagation_error": "B-A",
            "hls_half_subnormal_flush": True,
            "activation_scale_shift": 6,
        },
        file_count=len(files),
        total_bytes=sum(int(item["bytes"]) for item in files),
        files=files,
        next_gate="rerun only the complete Layer-0 HS64 A/B/C numerical gate over COM3",
    )
    manifest_path = output / "PACKAGE_MANIFEST.json"
    manifest_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    expected = {"PACKAGE_MANIFEST.json", *(item["path"] for item in files)}
    actual = {path.relative_to(output).as_posix() for path in output.rglob("*") if path.is_file()}
    if actual != expected:
        raise RuntimeError(f"candidate closure mismatch extra={sorted(actual-expected)} missing={sorted(expected-actual)}")
    for item in files:
        path = output / item["path"]
        if path.stat().st_size != item["bytes"] or sha256(path) != item["sha256"]:
            raise RuntimeError(f"candidate file identity mismatch: {item['path']}")
    result = {
        "gate": "M89-X1-HS64-ABC-candidate-package",
        "status": "PASS",
        "baseline_manifest_sha256": BASELINE_SHA256,
        "candidate_manifest_sha256": sha256(manifest_path),
        "file_count": len(files),
        "total_bytes": manifest["total_bytes"],
        "replacements": sorted(REPLACEMENTS),
    }
    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
