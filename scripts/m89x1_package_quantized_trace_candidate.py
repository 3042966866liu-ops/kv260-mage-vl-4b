#!/usr/bin/env python3
"""Package the all-layer quantized differential over the all-finite candidate."""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
from pathlib import Path


BASELINE_SHA256 = "3bf559404682573842e80893e3837c389d66c3d8274b83856c45555b2df115be"
REPLACEMENTS = {
    "runtime/m89x1_all_layer_quantized_board_diagnostic.py":
        "scripts/m89x1_all_layer_quantized_board_diagnostic.py",
    "runtime/run_m89x1_all_layer_quantized_diagnostic.sh":
        "scripts/run_m89x1_all_layer_quantized_diagnostic.sh",
    "auxiliary/m89x1_quantized_cpu_family_sketch.json":
        "deployment/mage_vl4b/artifacts/m89x1_quantized_cpu_family_sketch.json",
    "contracts/M89X1_QUANTIZED_CPU_ALL_LAYER_REFERENCE_RESULT.json":
        "deployment/mage_vl4b/M89X1_QUANTIZED_CPU_ALL_LAYER_REFERENCE_RESULT.json",
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
    baseline_manifest_path = baseline / "PACKAGE_MANIFEST.json"
    if sha256(baseline_manifest_path) != BASELINE_SHA256:
        raise RuntimeError("all-finite adaptive baseline identity mismatch")
    original = json.loads(baseline_manifest_path.read_text(encoding="utf-8"))
    reference = json.loads(
        (workspace / REPLACEMENTS[
            "contracts/M89X1_QUANTIZED_CPU_ALL_LAYER_REFERENCE_RESULT.json"
        ]).read_text(encoding="utf-8")
    )
    if (
        reference.get("status") != "MEASURED"
        or int(reference.get("capture_count", -1)) != 144
        or int(reference.get("quantized_cpu_token_id", -1)) != 18
    ):
        raise RuntimeError("quantized all-layer reference is not eligible")
    sketch = json.loads(
        (workspace / REPLACEMENTS[
            "auxiliary/m89x1_quantized_cpu_family_sketch.json"
        ]).read_text(encoding="utf-8")
    )
    if sketch.get("status") != "PASS" or int(sketch.get("tensor_count", -1)) != 144:
        raise RuntimeError("quantized all-layer sketch is not PASS")

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
        build="M89-X1-all-layer-quantized-differential/Z2",
        status="PASS_OFFLINE_ALL_LAYER_QUANTIZED_DIAGNOSTIC_REQUIRES_BOARD_MEASUREMENT",
        marker="M89X1_ALL_LAYER_QUANTIZED_DIAGNOSTIC_CANDIDATE_PACKAGE_PASS",
        baseline_manifest_sha256=BASELINE_SHA256,
        quantized_cpu_token_id=18,
        quantized_family_count=144,
        golden_sketch_sha256=sha256(
            output / "auxiliary/m89x1_quantized_cpu_family_sketch.json"
        ),
        deployed=False,
        board_state_changed=False,
        file_count=len(files),
        total_bytes=sum(int(item["bytes"]) for item in files),
        files=files,
        next_gate="run only the fixed-text 144-family quantized board differential over COM3",
    )
    manifest_path = output / "PACKAGE_MANIFEST.json"
    manifest_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    expected = {"PACKAGE_MANIFEST.json", *(item["path"] for item in files)}
    actual = {path.relative_to(output).as_posix() for path in output.rglob("*") if path.is_file()}
    if actual != expected:
        raise RuntimeError(
            f"candidate closure mismatch extra={sorted(actual-expected)} missing={sorted(expected-actual)}"
        )
    for item in files:
        path = output / item["path"]
        if path.stat().st_size != item["bytes"] or sha256(path) != item["sha256"]:
            raise RuntimeError(f"candidate file identity mismatch: {item['path']}")
    print(json.dumps({
        "gate": "M89-X1-all-layer-quantized-diagnostic-candidate-package",
        "status": "PASS",
        "baseline_manifest_sha256": BASELINE_SHA256,
        "candidate_manifest_sha256": sha256(manifest_path),
        "golden_sketch_sha256": manifest["golden_sketch_sha256"],
        "file_count": len(files),
        "total_bytes": manifest["total_bytes"],
        "replacements": sorted(REPLACEMENTS),
    }, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
