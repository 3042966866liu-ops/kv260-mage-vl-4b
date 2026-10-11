#!/usr/bin/env python3
"""Build a new immutable M89-X1 host-scale candidate from the verified baseline."""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
from pathlib import Path


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(8 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def copy_checked(source: Path, destination: Path) -> None:
    if not source.is_file():
        raise RuntimeError(f"required source missing: {source}")
    destination.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source, destination)
    if sha256(source) != sha256(destination):
        raise RuntimeError(f"copy hash mismatch: {destination}")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--workspace", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    root = args.workspace.resolve()
    baseline = root / "deployment" / "mage_vl4b" / "m89x_board_candidate"
    output = args.output.resolve()
    if output.exists():
        raise RuntimeError(f"output must be a new directory: {output}")
    baseline_manifest_path = baseline / "PACKAGE_MANIFEST.json"
    baseline_manifest = json.loads(baseline_manifest_path.read_text(encoding="utf-8"))
    if baseline_manifest.get("status") != "PASS_OFFLINE_BOARD_CANDIDATE_PACKAGE":
        raise RuntimeError("baseline package status is not PASS")
    for item in baseline_manifest["files"]:
        source = baseline / item["path"]
        if source.stat().st_size != int(item["bytes"]) or sha256(source) != item["sha256"]:
            raise RuntimeError(f"baseline identity failure: {source}")
        copy_checked(source, output / item["path"])

    runtime_source = root / "deployment" / "mage_vl4b" / "m89x_t32_runtime"
    for relative in ("contract_runtime.py", "board_runtime.py", "test_contract_runtime.py"):
        source = runtime_source / relative
        compile(source.read_text(encoding="utf-8"), str(source), "exec")
        copy_checked(source, output / "runtime" / relative)
    for relative in ("m89x1_layer0_tolerance_diagnostic.py",
                     "m89x1_qkv_reference_helper.py",
                     "m89x1_layer0_acceptance_gate.py"):
        source = root / "scripts" / relative
        compile(source.read_text(encoding="utf-8"), str(source), "exec")
        copy_checked(source, output / "runtime" / relative)
    runner_source = root / "scripts" / "run_m89x1_hostscale64_layer0_gate.sh"
    copy_checked(runner_source, output / "runtime" / runner_source.name)
    evidence_source = root / "deployment" / "mage_vl4b" / "M89X1_HOST_SCALE64_CSIM_RESULT.json"
    evidence = json.loads(evidence_source.read_text(encoding="utf-8"))
    if evidence.get("status") != "PASS" or evidence.get("candidate_build_id") != "0x4D395831":
        raise RuntimeError("host-scale CSim evidence is not accepted")
    copy_checked(evidence_source, output / "contracts" / evidence_source.name)

    readme = output / "README.md"
    readme.write_text(
        "# M89-X1 HS64 KV260 candidate (NOT DEPLOYED)\n\n"
        "This candidate keeps the verified X1 bitstream and all descriptor, DMA, FIFO and TLAST geometry unchanged. "
        "The host multiplies transmitted activation scales by 64 and divides parsed Linear outputs by 64, avoiding "
        "the Xilinx FP16 subnormal flush observed with RMSNorm-derived scales. Integer activation codes and packed "
        "weights are unchanged.\n\n"
        "Use only the fixed COM3 gate order. The next permitted board action is the previously rejected complete "
        "Layer-0 diagnostic; fixed-text E2E and Web remain prohibited until that gate passes. Stable boot, DTB, CMA, "
        "partitions and rollback must remain untouched.\n",
        encoding="utf-8",
    )

    forbidden = [path for path in output.rglob("*")
                 if path.is_file() and ("__pycache__" in path.parts or path.suffix == ".pyc")]
    if forbidden:
        raise RuntimeError(f"forbidden cache files in candidate: {forbidden}")
    files = []
    for path in sorted(item for item in output.rglob("*")
                       if item.is_file() and item.name != "PACKAGE_MANIFEST.json"):
        files.append({
            "path": path.relative_to(output).as_posix(),
            "bytes": path.stat().st_size,
            "sha256": sha256(path),
        })
    result = {
        "date": "2026-08-31",
        "build": "M89-X1-HS64/Z2",
        "status": "PASS_OFFLINE_BOARD_CANDIDATE_PACKAGE",
        "marker": "M89X1_HOST_SCALE64_CANDIDATE_PACKAGE_PASS",
        "deployed": False,
        "board_state_changed": False,
        "stable_rollback_required": True,
        "baseline_manifest_sha256": sha256(baseline_manifest_path),
        "fpga_build_id": "0x4D395831",
        "activation_scale_shift": 6,
        "activation_scale_factor": 64,
        "host_scale_csim_evidence": "contracts/M89X1_HOST_SCALE64_CSIM_RESULT.json",
        "file_count": len(files),
        "total_bytes": sum(int(item["bytes"]) for item in files),
        "large_payloads": baseline_manifest["large_payloads"],
        "files": files,
        "next_gate": "complete Layer-0 numerical board gate only over COM3; no E2E or Web before PASS"
    }
    manifest_path = output / "PACKAGE_MANIFEST.json"
    manifest_path.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(result["marker"])
    print(json.dumps({"files": len(files), "bytes": result["total_bytes"],
                      "manifest_sha256": sha256(manifest_path)}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
