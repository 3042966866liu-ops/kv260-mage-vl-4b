#!/usr/bin/env python3
"""Package the global adaptive-shift M89-X1 candidate for lower-gate revalidation."""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
from pathlib import Path


BASELINE_SHA256 = "1c0b4c2b2ceac741138a413d7db81c1ce67adf985d8d7f196ab0d47883ced444"
REPLACEMENTS = {
    "runtime/board_runtime.py": "deployment/mage_vl4b/m89x_t32_runtime/board_runtime.py",
    "runtime/text_e2e_gate.py": "deployment/mage_vl4b/m89x_t32_runtime/text_e2e_gate.py",
    "runtime/m89x1_fixed_text_acceptance_gate.py": "scripts/m89x1_fixed_text_acceptance_gate.py",
    "contracts/M89X1_HS64_FIXED_TEXT_TRACE_RESULT.json":
        "deployment/mage_vl4b/M89X1_HS64_FIXED_TEXT_TRACE_RESULT.json",
    "contracts/M89X1_ADAPTIVE_SCALE_POLICY_RESULT.json":
        "deployment/mage_vl4b/M89X1_ADAPTIVE_SCALE_POLICY_RESULT.json",
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
    baseline_manifest = baseline / "PACKAGE_MANIFEST.json"
    if sha256(baseline_manifest) != BASELINE_SHA256:
        raise RuntimeError("trace baseline identity mismatch")
    original = json.loads(baseline_manifest.read_text(encoding="utf-8"))
    adaptive_result = json.loads((workspace / REPLACEMENTS[
        "contracts/M89X1_ADAPTIVE_SCALE_POLICY_RESULT.json"]).read_text(encoding="utf-8"))
    if adaptive_result.get("status") != "PASS":
        raise RuntimeError("adaptive policy local gate is not PASS")
    shutil.copytree(baseline, output, ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
    for relative, source in REPLACEMENTS.items():
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
        build="M89-X1-adaptive-scale-fixed-text/Z2",
        status="PASS_OFFLINE_ADAPTIVE_SCALE_CANDIDATE_REQUIRES_LAYER0_REVALIDATION",
        marker="M89X1_ADAPTIVE_SCALE_CANDIDATE_PACKAGE_PASS",
        baseline_manifest_sha256=BASELINE_SHA256,
        activation_scale_policy="adaptive-power-of-two-finite-retry-v1",
        maximum_activation_scale_shift=6,
        minimum_activation_scale_shift=0,
        maximum_transmitted_active_scale=512.0,
        deployed=False,
        board_state_changed=False,
        file_count=len(files),
        total_bytes=sum(int(item["bytes"]) for item in files),
        files=files,
        next_gate="rerun complete Layer-0 before fixed-text E2E",
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
    print(json.dumps({
        "gate": "M89-X1-adaptive-scale-candidate-package",
        "status": "PASS",
        "baseline_manifest_sha256": BASELINE_SHA256,
        "candidate_manifest_sha256": sha256(manifest_path),
        "file_count": len(files),
        "total_bytes": manifest["total_bytes"],
        "replacements": sorted(REPLACEMENTS),
    }, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
