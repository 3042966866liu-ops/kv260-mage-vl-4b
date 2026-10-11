#!/usr/bin/env python3
"""Build a clean hash-locked M120 package for the first three COM3 gates."""

from __future__ import annotations

import hashlib
import json
import shutil
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "deployment/mage_vl4b/m120_text4b_board_candidate"
STAGING = ROOT / "tmp/m136_m120_text4b_board_candidate_staging"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(16 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def copy(source: Path, relative: str) -> None:
    if not source.is_file():
        raise RuntimeError(f"required source missing: {source}")
    target = STAGING / relative
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source, target)
    if sha256(source) != sha256(target):
        raise RuntimeError(f"copy identity mismatch: {relative}")


def main() -> int:
    if OUTPUT.exists() or STAGING.exists():
        raise RuntimeError("M136 output/staging must not pre-exist")
    implementation = json.loads(
        (ROOT / "deployment/mage_vl4b/M134_M120_M89X2_IMPLEMENTATION_GATE_RESULT.json").read_text(
            encoding="utf-8"
        )
    )
    if implementation.get("status") != "PASS" or implementation.get("build_id") != "0x4D395832":
        raise RuntimeError("M135 implementation gate is not passing")
    rtl = json.loads(
        (ROOT / "deployment/mage_vl4b/M134_M120_RTL_COSIM_GATE_RESULT.json").read_text(encoding="utf-8")
    )
    if rtl.get("status") != "PASS":
        raise RuntimeError("M134 RTL CoSim gate is not passing")

    implementation_root = ROOT / "deployment/mage_vl4b/m120_m89x2_board_candidate"
    copy(implementation_root / "overlay/m120_m89x2_t32.bit", "overlay/m120_m89x2_t32.bit")
    copy(implementation_root / "overlay/m120_m89x2_t32.hwh", "overlay/m120_m89x2_t32.hwh")

    runtime_root = ROOT / "deployment/mage_vl4b/m120_text4b_runtime"
    for name in (
        "m120_board_common.py", "m120_fixture.py", "m120_build_id_gate.py",
        "m120_fixture_gate.py", "m120_board_env_preflight.py", "run_m120_gate.sh",
    ):
        source = runtime_root / name
        copy(source, f"runtime/{name}")
        if source.suffix == ".py":
            compile(source.read_text(encoding="utf-8"), str(source), "exec")

    for name in (
        "M126_RUNTIME_CONTRACTS_RESULT.json",
        "M126_LANGUAGE_RUNTIME_CONTRACT_RESULT.json",
        "M126_LMHEAD_RUNTIME_CONTRACT_RESULT.json",
        "M128_M120_CSIM_FIXTURE_RESULT.json",
        "M130_M120_NUMERICAL_CSIM_RESULT.json",
        "M134_M120_RTL_COSIM_GATE_RESULT.json",
        "M134_M120_M89X2_IMPLEMENTATION_GATE_RESULT.json",
    ):
        copy(ROOT / "deployment/mage_vl4b" / name, f"contracts/{name}")
    for name in (
        "m126_m120_language_runtime_table.bin",
        "m126_m120_lmhead_runtime_table.bin",
    ):
        copy(ROOT / "deployment/mage_vl4b/artifacts" / name, f"contracts/{name}")
    copy(
        ROOT / "deployment/mage_vl4b/artifacts/m128_m120_real_record_csim_fixture.bin",
        "reference/m128_m120_real_record_csim_fixture.bin",
    )

    fixture_result = json.loads(
        (ROOT / "deployment/mage_vl4b/M128_M120_CSIM_FIXTURE_RESULT.json").read_text(encoding="utf-8")
    )
    fixture_path = STAGING / "reference/m128_m120_real_record_csim_fixture.bin"
    if sha256(fixture_path) != fixture_result["fixture_sha256"]:
        raise RuntimeError("M128 fixture identity mismatch")

    readme = """# M120/M89X2 initial KV260 board candidate

This immutable package is limited to the first three COM3 gates: the smallest
legal Build-ID transaction, one real M120 descriptor, and one real M120 chain.
It is not full Layer-0, fixed-text, performance, video, or Web evidence.

The runner performs exactly one environment preflight in the same authorized
terminal, verifies every package file hash, selects the PYNQ-venv xclbinutil,
then loads the overlay.  It does not change boot, DTB, CMA, partitions,
services, or the stable rollback directory.
"""
    (STAGING / "README.md").write_text(readme, encoding="utf-8")

    files = []
    for path in sorted(p for p in STAGING.rglob("*") if p.is_file()):
        relative = path.relative_to(STAGING).as_posix()
        if "__pycache__" in path.parts or path.suffix == ".pyc":
            raise RuntimeError(f"cache file entered staging: {relative}")
        files.append({"path": relative, "bytes": path.stat().st_size, "sha256": sha256(path)})
    manifest = {
        "date": "2026-09-01",
        "build": "M120/M89X2",
        "status": "PASS_OFFLINE_INITIAL_BOARD_GATE_PACKAGE",
        "marker": "M136_M120_INITIAL_BOARD_PACKAGE_PASS",
        "deployed": False,
        "board_state_changed": False,
        "stable_rollback_required": True,
        "allowed_gate_order": ["build-id", "single-descriptor", "single-chain"],
        "file_count": len(files),
        "total_bytes": sum(item["bytes"] for item in files),
        "files": files,
        "next_gate": "COM3 build-id only; single-descriptor is prohibited until that PASS.",
    }
    manifest_path = STAGING / "PACKAGE_MANIFEST.json"
    manifest_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    shutil.move(str(STAGING), str(OUTPUT))
    print(manifest["marker"])
    print(f"package={OUTPUT}")
    print(f"manifest_sha256={sha256(OUTPUT / 'PACKAGE_MANIFEST.json')}")
    print(f"file_count={manifest['file_count']} total_bytes={manifest['total_bytes']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

