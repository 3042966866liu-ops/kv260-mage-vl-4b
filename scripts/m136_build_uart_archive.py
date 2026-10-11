#!/usr/bin/env python3
"""Create a deterministic UART archive from the verified M136 package."""

from __future__ import annotations

import gzip
import hashlib
import io
import json
import tarfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PACKAGE = ROOT / "deployment/mage_vl4b/m120_text4b_board_candidate"
OUTPUT = ROOT / "tmp/m136_uart/m120_text4b_board_candidate.tar.gz"
RESULT = ROOT / "deployment/mage_vl4b/M136_M120_UART_ARCHIVE_RESULT.json"
EXPECTED_MANIFEST = "7600ba1af87680fe1294ae6dc88f8e0968f23b2e38ca48dbfd316e351ea76e3e"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(16 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def main() -> int:
    if OUTPUT.exists():
        raise RuntimeError(f"output already exists: {OUTPUT}")
    manifest_path = PACKAGE / "PACKAGE_MANIFEST.json"
    if sha256(manifest_path) != EXPECTED_MANIFEST:
        raise RuntimeError("package manifest drift")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    expected = {"PACKAGE_MANIFEST.json", *(item["path"] for item in manifest["files"])}
    actual = {p.relative_to(PACKAGE).as_posix() for p in PACKAGE.rglob("*") if p.is_file()}
    if actual != expected:
        raise RuntimeError("package closure mismatch")

    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    with OUTPUT.open("wb") as raw:
        with gzip.GzipFile(filename="", mode="wb", fileobj=raw, mtime=0, compresslevel=9) as compressed:
            with tarfile.open(fileobj=compressed, mode="w") as archive:
                for relative in sorted(actual):
                    source = PACKAGE / relative
                    info = tarfile.TarInfo(f"m120_text4b_board_candidate/{relative}")
                    info.size = source.stat().st_size
                    info.mode = 0o755 if relative.endswith(".sh") or relative.endswith(".py") else 0o644
                    info.mtime = 0
                    info.uid = info.gid = 0
                    info.uname = info.gname = ""
                    with source.open("rb") as stream:
                        archive.addfile(info, stream)
    result = {
        "date": "2026-09-01",
        "gate": "M136-M120-UART-archive",
        "status": "PASS",
        "package_manifest_sha256": EXPECTED_MANIFEST,
        "archive": str(OUTPUT.relative_to(ROOT)).replace("\\", "/"),
        "archive_bytes": OUTPUT.stat().st_size,
        "archive_sha256": sha256(OUTPUT),
        "member_count": len(actual),
        "board_state_changed": False,
    }
    RESULT.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print("M136_M120_UART_ARCHIVE_PASS")
    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

