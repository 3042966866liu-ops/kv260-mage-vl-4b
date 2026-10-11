#!/usr/bin/env python3
"""Build the clean, hash-closed M198 UART bootstrap."""

import hashlib
import json
import os
import shutil
import sys
from pathlib import Path

sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "tmp/m198_ps_vision/m198_gate"
RESULT = ROOT / "deployment/mage_vl4b/M198_PS_VISION_BOOTSTRAP_RESULT.json"
M192 = ROOT / "deployment/mage_vl4b/M192_M181_PS_VISION_BOARD_RESULT_02.json"
M197 = ROOT / "deployment/mage_vl4b/m197_ps_vision_fp32_block_candidate"
M192_SHA = "bc506174b9148d565b2f258b99417845347355f4572d0245db8e32d1d24401bf"
LAYERS = list(range(6, 24))


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(4 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def main() -> int:
    if sha256(M192) != M192_SHA or json.loads(M192.read_text())["status"] != "PASS":
        raise RuntimeError("M198 exact M192 predecessor mismatch")
    offline = M197 / "M197_OFFLINE_FP32_LAYERS_06_23.json"
    policy = json.loads(offline.read_text())
    if policy.get("status") != "PASS" or policy.get("fp32_encoder_layers") != LAYERS:
        raise RuntimeError("M198 offline M197 policy is not PASS")
    partial = OUT.with_name(OUT.name + ".partial")
    if OUT.exists() or partial.exists():
        raise RuntimeError("M198 clean output required")
    partial.mkdir(parents=True)
    sources = {
        "m198_video_ps_vision_board_gate.py": ROOT / "scripts/m198_video_ps_vision_board_gate.py",
        "m198_run_video_ps_vision_board_gate.sh": ROOT / "scripts/m198_run_video_ps_vision_board_gate.sh",
        "m198_verify_bootstrap.py": ROOT / "scripts/m198_verify_bootstrap.py",
        "ps_vision_runtime.py": M197 / "ps_vision_runtime.py",
        "test_ps_vision_runtime.py": M197 / "test_ps_vision_runtime.py",
        "M192_M181_PS_VISION_BOARD_RESULT_02.json": M192,
        "M197_OFFLINE_FP32_LAYERS_06_23.json": offline,
    }
    entries = []
    for name, source in sources.items():
        destination = partial / name
        shutil.copyfile(source, destination)
        entries.append({"path": name, "bytes": destination.stat().st_size, "sha256": sha256(destination)})
    manifest = {
        "date": "2026-09-01",
        "gate": "M198-M197-FP32-block-PS-vision-bootstrap",
        "status": "PASS",
        "m192_sha256": M192_SHA,
        "fp32_encoder_layers": LAYERS,
        "files": entries,
        "file_count": len(entries),
        "total_bytes": sum(item["bytes"] for item in entries),
        "excluded_patterns": ["__pycache__", "*.pyc", "*.log"],
    }
    (partial / "PACKAGE_MANIFEST.json").write_text(json.dumps(manifest, indent=2) + "\n")
    os.replace(partial, OUT)
    result = {
        "date": "2026-09-01",
        "gate": "M198-M197-FP32-block-PS-vision-bootstrap-build",
        "status": "PASS",
        "directory": OUT.relative_to(ROOT).as_posix(),
        "package_manifest_sha256": sha256(OUT / "PACKAGE_MANIFEST.json"),
        "m192_sha256": M192_SHA,
        "fp32_encoder_layers": LAYERS,
        "file_count": len(entries),
        "total_bytes": manifest["total_bytes"],
        "board_state_changed": False,
    }
    temporary = RESULT.with_name(RESULT.name + ".partial")
    temporary.write_text(json.dumps(result, indent=2) + "\n")
    os.replace(temporary, RESULT)
    print(json.dumps(result, indent=2))
    print("M198_BOOTSTRAP_BUILD_PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
