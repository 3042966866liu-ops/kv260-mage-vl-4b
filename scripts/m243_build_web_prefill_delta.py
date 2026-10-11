#!/usr/bin/env python3
"""Build the clean M243 Web Prefill integration delta."""

from __future__ import annotations

import hashlib
import json
import shutil
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "deployment/mage_vl4b/m243_web_prefill_source"
DEST = ROOT / "deployment/mage_vl4b/m243_web_prefill_board_candidate"
RESULT = ROOT / "deployment/mage_vl4b/M243_WEB_PREFILL_BUILD_RESULT.json"
M242_RESULT = ROOT / "deployment/mage_vl4b/M242_M241_FIXED_TEXT_BOARD_RESULT_03.json"
M242_HASH = "f36b93758c93ec5986644ee170d4553dc07056532e35fdac281bd6e6722b6312"


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


if sha(M242_RESULT) != M242_HASH:
    raise RuntimeError("M243 exact M242 formal predecessor hash mismatch")
m242 = json.loads(M242_RESULT.read_text(encoding="utf-8"))
if m242.get("status") != "PASS_SERVICE_RESTORED":
    raise RuntimeError("M243 M242 predecessor is not accepted")
if DEST.exists():
    shutil.rmtree(DEST)
DEST.mkdir(parents=True)
for source in sorted(SOURCE.iterdir()):
    if source.is_file() and source.suffix not in {".pyc"}:
        shutil.copy2(source, DEST / source.name)
files = []
for path in sorted(DEST.rglob("*")):
    if path.is_file():
        if "__pycache__" in path.parts or path.suffix == ".pyc":
            raise RuntimeError("M243 forbidden Python cache")
        files.append({"path": path.relative_to(DEST).as_posix(), "bytes": path.stat().st_size, "sha256": sha(path)})
manifest = {
    "date": "2026-09-02",
    "gate": "M243-web-prefill-runtime-delta",
    "status": "PASS",
    "build_id": "0x4D395832",
    "m242_formal_result_sha256": M242_HASH,
    "m242_delta_manifest_sha256": "ef94f50608dcda4ae33d3d133434429304bb72dbeb6def90666d7613aadfe510",
    "m223_manifest_sha256": "debc3f1d1b783af028ad47a5a7c3bdb3c9012ee8febdecef39367c4bcc25b53f",
    "m227_manifest_sha256": "0bab466470fe09ef1b548921235a365ac3832c6264bf2e3a16ee19a6a3aad13c",
    "t64_used": False,
    "files": files,
}
(DEST / "PACKAGE_MANIFEST.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
value = {
    "date": "2026-09-02",
    "gate": "M243-web-prefill-runtime-delta-build",
    "status": "PASS",
    "directory": DEST.relative_to(ROOT).as_posix(),
    "package_manifest_sha256": sha(DEST / "PACKAGE_MANIFEST.json"),
    "file_count": len(files),
    "total_bytes": sum(item["bytes"] for item in files),
    "stable_rollback_preserved": True,
}
RESULT.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
print(json.dumps(value, ensure_ascii=False))
