#!/usr/bin/env python3
"""Build the bounded, immutable four-frame companion to the v7 release TAR."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
import tarfile


WORKSPACE = Path(__file__).resolve().parents[1]
ROOT = WORKSPACE / "release_staging/m328_release_video_addon_20260926_v3"
ARCHIVE = WORKSPACE / "release_staging/m328_release_video_addon_20260926_v3.tar"
REPORT = WORKSPACE / "deployment/mage_vl4b/M328_VIDEO_ADDON_BUILD_RESULT_V3.json"
FILES = [
    "run_fixed_video.py",
    "fixtures/frame_00_0068_rgb448.npy",
    "fixtures/frame_01_0102_rgb448.npy",
    "fixtures/frame_02_0137_rgb448.npy",
    "fixtures/frame_03_0171_rgb448.npy",
]


def sha(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(4 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def main() -> None:
    if ARCHIVE.exists() or REPORT.exists() or (ROOT / "PACKAGE_MANIFEST.json").exists():
        raise RuntimeError("immutable M328 output already exists")
    observed = sorted(p.relative_to(ROOT).as_posix() for p in ROOT.rglob("*") if p.is_file())
    if observed != sorted(FILES):
        raise RuntimeError(f"add-on whitelist mismatch: {observed}")
    entries = [{"path": name, "bytes": (ROOT / name).stat().st_size, "sha256": sha(ROOT / name)}
               for name in FILES]
    manifest = {"schema": "tellme-m328-release-fixed-video-addon-v1",
                "base_release_archive_sha256": "c487e16bcc18698808d7c48822e355c8b6cf291633b00d661f372f7280d41145",
                "build_id": "0x4D395832", "file_count": len(entries),
                "payload_bytes": sum(item["bytes"] for item in entries), "files": entries}
    (ROOT / "PACKAGE_MANIFEST.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    with tarfile.open(ARCHIVE, "w") as archive:
        for name in ["PACKAGE_MANIFEST.json", *FILES]:
            path = ROOT / name
            info = tarfile.TarInfo(name)
            info.size = path.stat().st_size
            info.mode = 0o644
            info.uid = info.gid = 0
            info.uname = info.gname = ""
            info.mtime = 0
            with path.open("rb") as stream:
                archive.addfile(info, stream)
    result = {"gate": "M328-release-video-addon-build", "status": "PASS",
              "archive": str(ARCHIVE.relative_to(WORKSPACE)).replace("\\", "/"),
              "archive_bytes": ARCHIVE.stat().st_size, "archive_sha256": sha(ARCHIVE),
              "manifest_sha256": sha(ROOT / "PACKAGE_MANIFEST.json"),
              "file_count": len(entries), "payload_bytes": manifest["payload_bytes"],
              "ordered_frame_tensor_sha256": "5911485955780036ac4c8990bcaa248667f2e86bd1fd6f9b0783002553b4adff"}
    REPORT.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
