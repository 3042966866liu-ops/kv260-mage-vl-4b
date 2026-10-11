#!/usr/bin/env python3
"""Build the clean M246 constrained knife-classifier runtime delta."""

from __future__ import annotations

import hashlib
import json
import shutil
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "deployment/mage_vl4b/m246_knife_binary_source"
ALARM = ROOT / "deployment/mage_vl4b/m245_knife_alarm_source"
DEST = ROOT / "deployment/mage_vl4b/m246_knife_binary_board_candidate"
RESULT = ROOT / "deployment/mage_vl4b/M246_KNIFE_BINARY_BUILD_RESULT.json"
M243 = ROOT / "deployment/mage_vl4b/M243_WEB_PREFILL_BOARD_RESULT_05.json"
M244 = ROOT / "deployment/mage_vl4b/M244_M243_FIXED_FOUR_FRAME_BOARD_RESULT_02.json"
M243_SHA = "80ea2b8e1d142ef4400aa7e545cf62b3c6ae7a5531e4466df06b35758df096c6"
M244_SHA = "b134fc00f7e2be60d9444f0e81203561972455d78907cdb6515462a98243e392"


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


if sha(M243) != M243_SHA:
    raise RuntimeError("M246 exact M243 predecessor hash mismatch")
if sha(M244) != M244_SHA:
    raise RuntimeError("M246 exact M244 predecessor hash mismatch")
m243 = json.loads(M243.read_text(encoding="utf-8"))
m244 = json.loads(M244.read_text(encoding="utf-8"))
if m243.get("status") != "PASS" or m243.get("frames_submitted") != 0:
    raise RuntimeError("M246 M243 predecessor is not accepted")
if not (
    m244.get("functional_status") == "FAIL"
    and len([e for e in m244.get("events", []) if e.get("event") == "vision_layer_pass"]) == 24
    and m244.get("window_error", [{}])[0].get("error")
    == "RuntimeError: M152 generated no non-EOS token"
):
    raise RuntimeError("M246 M244 predecessor failure identity mismatch")
if DEST.exists():
    raise RuntimeError(f"M246 clean destination already exists: {DEST}")
DEST.mkdir(parents=True)

for name in (
    "m246_knife_binary.py",
    "m246_video_server.py",
    "m246_verify_package.py",
    "m246_runtime_ready_probe.py",
    "run_m246_knife_runtime_gate.sh",
):
    shutil.copy2(SOURCE / name, DEST / name)
shutil.copy2(ALARM / "knife_alarm.py", DEST / "knife_alarm.py")
shutil.copy2(ALARM / "M245_KNIFE_ALARM_CONTRACT.json", DEST / "M245_KNIFE_ALARM_CONTRACT.json")
shutil.copy2(M244, DEST / "M244_PREDECESSOR_RESULT.json")

files = []
for path in sorted(DEST.rglob("*")):
    if not path.is_file():
        continue
    if "__pycache__" in path.parts or path.suffix == ".pyc":
        raise RuntimeError("M246 forbidden Python cache")
    files.append({
        "path": path.relative_to(DEST).as_posix(),
        "bytes": path.stat().st_size,
        "sha256": sha(path),
    })
manifest = {
    "date": "2026-09-02",
    "gate": "M246-constrained-knife-runtime-delta",
    "status": "PASS",
    "build_id": "0x4D395832",
    "m243_formal_result_sha256": M243_SHA,
    "m244_formal_result_sha256": M244_SHA,
    "knife_no_token_id": 15,
    "knife_yes_token_id": 16,
    "knife_score_calibrated": False,
    "t64_used": False,
    "files": files,
}
(DEST / "PACKAGE_MANIFEST.json").write_text(
    json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
)
value = {
    "date": "2026-09-02",
    "gate": "M246-constrained-knife-runtime-delta-build",
    "status": "PASS",
    "directory": DEST.relative_to(ROOT).as_posix(),
    "package_manifest_sha256": sha(DEST / "PACKAGE_MANIFEST.json"),
    "file_count": len(files),
    "total_bytes": sum(item["bytes"] for item in files),
    "stable_rollback_preserved": True,
}
RESULT.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
print(json.dumps(value, ensure_ascii=False))

