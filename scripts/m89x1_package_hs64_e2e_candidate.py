#!/usr/bin/env python3
"""Create a clean fixed-text E2E candidate from the accepted HS64 A/B/C package."""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
from pathlib import Path


BASELINE_SHA256 = "afd5a46621af364058d4eac77e946c7f35ad355e626e0404256b00d872ae5bd0"
LAYER0_RESULT_SHA256 = "384e74c84873c96da6bef2f6d4c2fffcdb2474be39e18bf8f8fcae063281c1cc"
ADDITIONS = {
    "runtime/m89x1_fixed_text_acceptance_gate.py": "scripts/m89x1_fixed_text_acceptance_gate.py",
    "runtime/run_m89x1_hostscale64_fixed_text_e2e_gate.sh":
        "scripts/run_m89x1_hostscale64_fixed_text_e2e_gate.sh",
    "contracts/M89X1_HS64_ABC_LAYER0_GATE_RESULT.json":
        "deployment/mage_vl4b/M89X1_HS64_ABC_LAYER0_GATE_RESULT.json",
    "contracts/M89X1_HS64_ABC_LAYER0_MEASUREMENT_RESULT.json":
        "deployment/mage_vl4b/M89X1_HS64_ABC_LAYER0_MEASUREMENT_RESULT.json",
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
    workspace = args.workspace.resolve()
    baseline = args.baseline.resolve()
    output = args.output.resolve()
    if output.exists():
        raise RuntimeError(f"output already exists: {output}")
    baseline_manifest = baseline / "PACKAGE_MANIFEST.json"
    if sha256(baseline_manifest) != BASELINE_SHA256:
        raise RuntimeError("accepted HS64 A/B/C baseline identity mismatch")
    layer0_result = workspace / ADDITIONS["contracts/M89X1_HS64_ABC_LAYER0_GATE_RESULT.json"]
    if sha256(layer0_result) != LAYER0_RESULT_SHA256:
        raise RuntimeError("accepted Layer-0 result identity mismatch")
    layer0 = json.loads(layer0_result.read_text(encoding="utf-8"))
    if layer0.get("status") != "PASS" or layer0.get("candidate_build_id") != "0x4d395831":
        raise RuntimeError("complete Layer-0 acceptance prerequisite failed")

    original = json.loads(baseline_manifest.read_text(encoding="utf-8"))
    shutil.copytree(baseline, output, ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
    for relative, source in ADDITIONS.items():
        destination = output / relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(workspace / source, destination)

    files = []
    for path in sorted(output.rglob("*")):
        if not path.is_file() or path.name == "PACKAGE_MANIFEST.json":
            continue
        relative = path.relative_to(output).as_posix()
        if "__pycache__" in path.parts or path.suffix == ".pyc":
            raise RuntimeError(f"forbidden cache in candidate: {relative}")
        files.append({"path": relative, "bytes": path.stat().st_size, "sha256": sha256(path)})
    manifest = dict(original)
    manifest.update(
        build="M89-X1-HS64-fixed-text-E2E/Z2",
        status="PASS_LAYER0_BOARD_ANCHORED_FIXED_TEXT_E2E_CANDIDATE",
        marker="M89X1_HOST_SCALE64_FIXED_TEXT_E2E_CANDIDATE_PACKAGE_PASS",
        baseline_manifest_sha256=BASELINE_SHA256,
        accepted_layer0_result_sha256=LAYER0_RESULT_SHA256,
        deployed=False,
        board_state_changed=False,
        file_count=len(files),
        total_bytes=sum(int(item["bytes"]) for item in files),
        files=files,
        next_gate="run only the fixed 30-token/one-token E2E gate over COM3",
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
        "gate": "M89-X1-HS64-fixed-text-E2E-candidate-package",
        "status": "PASS",
        "baseline_manifest_sha256": BASELINE_SHA256,
        "candidate_manifest_sha256": sha256(manifest_path),
        "file_count": len(files),
        "total_bytes": manifest["total_bytes"],
        "additions": sorted(ADDITIONS),
    }
    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
