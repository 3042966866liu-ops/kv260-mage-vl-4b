#!/usr/bin/env python3
"""Create and verify a deterministic UART archive for the M145 Layer-0 package."""

from __future__ import annotations

import gzip
import hashlib
import json
import os
import tarfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PACKAGE = ROOT / "deployment/mage_vl4b/m120_text4b_layer0_board_candidate"
TOP = "m120_text4b_layer0_board_candidate"
OUTPUT = ROOT / "tmp/m154_uart/m120_text4b_layer0_board_candidate.tar.gz"
RESULT = ROOT / "deployment/mage_vl4b/M154_M120_LAYER0_UART_ARCHIVE_RESULT.json"
EXPECTED_MANIFEST = "732b881d3507eaa12b8488e9224835ac115b686a003c748c9fa05a9793041d13"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(16 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def verify_package() -> tuple[dict, set[str]]:
    manifest_path = PACKAGE / "PACKAGE_MANIFEST.json"
    if sha256(manifest_path) != EXPECTED_MANIFEST:
        raise RuntimeError("M145 package manifest drift")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if manifest.get("status") != "OFFLINE_PACKAGE_PASS_BOARD_NOT_EXECUTED":
        raise RuntimeError("M145 package status is not accepted")
    if manifest.get("build_id") != "0x4D395832" or manifest.get("required_predecessor") != "M140_M120_SINGLE_CHAIN_BOARD_RESULT_01.json status=PASS":
        raise RuntimeError("M145 package identity/predecessor mismatch")
    expected = {"PACKAGE_MANIFEST.json", *(item["path"] for item in manifest["files"])}
    actual = {path.relative_to(PACKAGE).as_posix() for path in PACKAGE.rglob("*") if path.is_file()}
    if actual != expected:
        raise RuntimeError("M145 package closure mismatch")
    for item in manifest["files"]:
        path = PACKAGE / item["path"]
        if path.stat().st_size != int(item["bytes"]) or sha256(path) != item["sha256"]:
            raise RuntimeError(f"M145 package member mismatch: {item['path']}")
    if any("__pycache__" in Path(relative).parts or relative.endswith(".pyc") for relative in actual):
        raise RuntimeError("M145 package contains forbidden cache paths")
    return manifest, actual


def main() -> int:
    manifest, actual = verify_package()
    if OUTPUT.exists():
        raise RuntimeError(f"refusing to overwrite archive: {OUTPUT}")
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    with OUTPUT.open("xb") as raw:
        with gzip.GzipFile(filename="", mode="wb", fileobj=raw, mtime=0, compresslevel=9) as compressed:
            with tarfile.open(fileobj=compressed, mode="w") as archive:
                for relative in sorted(actual):
                    source = PACKAGE / relative
                    info = tarfile.TarInfo(f"{TOP}/{relative}")
                    info.size = source.stat().st_size
                    info.mode = 0o755 if relative.endswith((".sh", ".py")) else 0o644
                    info.mtime = 0
                    info.uid = info.gid = 0
                    info.uname = info.gname = ""
                    with source.open("rb") as stream:
                        archive.addfile(info, stream)
    result = {
        "date": "2026-09-01",
        "gate": "M154-M120-Layer0-UART-archive",
        "status": "PASS",
        "classification": "Deterministic verified Layer-0 control-package archive only; not transfer, board, Layer-0, fixed-text, video or Web evidence.",
        "build_id": "0x4D395832",
        "package_manifest_sha256": EXPECTED_MANIFEST,
        "archive": OUTPUT.relative_to(ROOT).as_posix(),
        "archive_bytes": OUTPUT.stat().st_size,
        "archive_sha256": sha256(OUTPUT),
        "member_count": len(actual),
        "source_file_count": len(manifest["files"]),
        "required_predecessor": "M140 single-chain real-board PASS",
        "board_state_changed": False,
    }
    RESULT.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, indent=2))
    print("M154_M120_LAYER0_UART_ARCHIVE_PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
