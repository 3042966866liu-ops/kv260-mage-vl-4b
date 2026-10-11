#!/usr/bin/env python3
"""Build an immutable, whitelisted M333 CPU-only board test archive."""

import hashlib
import io
import json
from pathlib import Path
import tarfile

ROOT = Path(__file__).resolve().parents[2]
BASE = ROOT / "deployment/mage_vl4b/optimization_v1"
SOURCE = BASE / "candidates/M333-web-review-loop-01"
OUT = BASE / "runs/M333-web-review-loop-board-01"
FILES = {
    "deployment/m333/m333_review_bridge.py": SOURCE / "m333_review_bridge.py",
    "deployment/m333/m333_video_server.py": SOURCE / "m333_video_server.py",
    "deployment/m333/test_m333_review_bridge.py": SOURCE / "test_m333_review_bridge.py",
    "deployment/m333/test_m333_http_sse.py": SOURCE / "test_m333_http_sse.py",
    "tmp/m223_realtime/m223_realtime_delta/live_stream_core.py":
        ROOT / "release_staging/kv260-mage-vl-4b/tmp/m223_realtime/m223_realtime_delta/live_stream_core.py",
    "tmp/m223_realtime/m223_realtime_delta/video_server.py":
        ROOT / "release_staging/kv260-mage-vl-4b/tmp/m223_realtime/m223_realtime_delta/video_server.py",
}


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    archive = OUT / "M333_OFFLINE_BOARD_PACKAGE.tar.gz"
    contract = OUT / "TRANSFER_CONTRACT.json"
    if archive.exists() or contract.exists():
        raise FileExistsError("immutable M333 board package already exists")
    rows = []
    with tarfile.open(archive, "w:gz") as handle:
        for name, source in sorted(FILES.items()):
            raw = source.read_bytes()
            rows.append({"path": name, "bytes": len(raw),
                         "sha256": hashlib.sha256(raw).hexdigest()})
            info = tarfile.TarInfo(name)
            info.size = len(raw)
            info.mode = 0o644
            handle.addfile(info, io.BytesIO(raw))
    value = {
        "gate": "M333-offline-board-package",
        "scope": "CPU-only scheduler and actual HTTP Handler with fake model; no overlay",
        "archive_bytes": archive.stat().st_size,
        "archive_sha256": hashlib.sha256(archive.read_bytes()).hexdigest(),
        "files": rows,
    }
    contract.write_text(json.dumps(value, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"archive": str(archive), "contract_sha256":
                      hashlib.sha256(contract.read_bytes()).hexdigest(), **value}))


if __name__ == "__main__":
    main()
