#!/usr/bin/env python3
"""Build the clean M190 COM3-controlled receiver bootstrap."""

from __future__ import annotations

import hashlib
import json
import os
import shutil
import sys
from pathlib import Path


sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "tmp/m190_runtime/m190_bootstrap"
RESULT = ROOT / "deployment/mage_vl4b/M190_RUNTIME_BOOTSTRAP_RESULT.json"
BUNDLE_RESULT = ROOT / "deployment/mage_vl4b/M189_ARM64_TORCH_BUNDLE_RESULT.json"
BUNDLE_SHA = "88c3fefaae94a475751bef3348e0048f30fc90bb1f27caa20e79f2e0f77361ba"


def sha256(path: Path) -> str:
    value = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(4 << 20), b""):
            value.update(block)
    return value.hexdigest()


def atomic_json(path: Path, value: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + ".partial")
    temporary.write_text(json.dumps(value, indent=2) + "\n", encoding="utf-8")
    os.replace(temporary, path)


def main() -> int:
    bundle_result = json.loads(BUNDLE_RESULT.read_text())
    if bundle_result.get("status") != "PASS" or bundle_result.get("bundle_manifest_sha256") != BUNDLE_SHA:
        raise RuntimeError("M190 exact M189 predecessor mismatch")
    if OUTPUT.exists() or OUTPUT.with_name(OUTPUT.name + ".partial").exists():
        raise RuntimeError("M190 clean bootstrap output required")
    staging = OUTPUT.with_name(OUTPUT.name + ".partial")
    staging.mkdir(parents=True)
    sources = {
        "m190_runtime_board_receiver.py": ROOT / "scripts/m190_runtime_board_receiver.py",
        "m190_run_runtime_receiver.sh": ROOT / "scripts/m190_run_runtime_receiver.sh",
        "m190_verify_runtime_bootstrap.py": ROOT / "scripts/m190_verify_runtime_bootstrap.py",
    }
    entries = []
    for name, source in sources.items():
        target = staging / name
        shutil.copyfile(source, target)
        entries.append({"path": name, "bytes": target.stat().st_size, "sha256": sha256(target)})
    manifest = {
        "date": "2026-09-01",
        "gate": "M190-ARM64-runtime-board-bootstrap",
        "status": "PASS",
        "m189_bundle_manifest_sha256": BUNDLE_SHA,
        "listen": "192.168.0.2:8768",
        "allowed_peer": "192.168.0.10",
        "files": entries,
        "file_count": len(entries),
    }
    (staging / "PACKAGE_MANIFEST.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    os.replace(staging, OUTPUT)
    result = {
        "date": "2026-09-01",
        "gate": "M190-ARM64-runtime-board-bootstrap-build",
        "status": "PASS",
        "classification": "COM3-controlled receiver bootstrap only; no board install or inference.",
        "directory": OUTPUT.relative_to(ROOT).as_posix(),
        "package_manifest_sha256": sha256(OUTPUT / "PACKAGE_MANIFEST.json"),
        "m189_bundle_manifest_sha256": BUNDLE_SHA,
        "file_count": 3,
        "board_state_changed": False,
    }
    atomic_json(RESULT, result)
    print(json.dumps(result, indent=2))
    print("M190_RUNTIME_BOOTSTRAP_BUILD_PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
