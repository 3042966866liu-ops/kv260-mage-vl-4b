#!/usr/bin/env python3
"""Read-only identity check for the experimental Decode-one code delivery."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "hls/mage_decode_op01_one"
PACKAGE = ROOT / "deployment/mage_vl4b/optimization_v1/candidates/OP01-decode-one-ab-01"
RUNS = ROOT / "deployment/mage_vl4b/optimization_v1/runs"
BUILD = "0x4F503131"
STABLE = "0x4D395832"


def digest(path: Path) -> str:
    value = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(8 << 20), b""):
            value.update(chunk)
    return value.hexdigest()


def read(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def main() -> int:
    source_manifest = read(SOURCE / "SOURCE_MANIFEST.json")
    package_manifest = read(PACKAGE / "PACKAGE_MANIFEST.json")
    artifact_manifest = read(PACKAGE / "ARTIFACT_MANIFEST.json")
    stable = read(RUNS / "OP01-decode-one-ab-stable-01/result.json")
    candidate = read(RUNS / "OP01-decode-one-ab-candidate-01/result.json")
    comparison = (RUNS / "OP01-decode-one-ab-comparison-01/REPORT.md").read_text(encoding="utf-8")

    assert source_manifest["build_id"] == BUILD
    assert package_manifest["build_id"] == artifact_manifest["build_id"] == BUILD
    assert source_manifest["config"].startswith("bit24=1")
    assert package_manifest["capacity_status"] == artifact_manifest["capacity_status"] == "STOPPED_BY_USER_NOT_PASS"
    assert not package_manifest["formal_promotion_allowed"] and not artifact_manifest["formal_promotion_allowed"]
    source_files = {entry["path"]: entry for entry in source_manifest["files"]}
    for name in ("decode_one.cpp", "decode_one.hpp"):
        assert digest(SOURCE / name) == source_files[name]["sha256"]
    assert len(package_manifest["files"]) == package_manifest["file_count"]
    assert sum(entry["bytes"] for entry in package_manifest["files"]) == package_manifest["total_bytes"]
    for entry in package_manifest["files"]:
        path = PACKAGE / entry["path"]
        assert path.is_file() and path.stat().st_size == entry["bytes"]
        assert digest(path) == entry["sha256"], entry["path"]
    package_files = {entry["path"]: entry for entry in package_manifest["files"]}
    for name in ("decode_one_runtime_adapter.py", "decode_one_policy.py", "candidate_base.py",
                 "overlay/op01_decode_one.bit", "overlay/op01_decode_one.hwh"):
        assert name in package_files
    assert package_files["overlay/op01_decode_one.bit"]["sha256"] == artifact_manifest["files"][0]["sha256"]
    assert stable["status"] == "PASS_STABLE_DECODE_REFERENCE" and stable["build_id"] == STABLE
    assert candidate["status"] == "PASS_CANDIDATE_DECODE_EXACT" and candidate["build_id"] == BUILD
    assert stable["stable_restored"] and candidate["stable_restored"]
    assert not stable["performance_pass"] and not candidate["performance_pass"]
    assert "完整logits逐字节一致" in comparison

    print("M323_DECODE_ONE_CODE_IDENTITY_PASS")
    print(f"build={BUILD} source_files=2 package_files={package_manifest['file_count']} ")
    print(f"candidate_s={candidate['decode_seconds']:.6f} stable_s={stable['decode_seconds']:.6f}")
    print("formal_promotion=false capacity=STOPPED_BY_USER_NOT_PASS stable_restored=true")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
