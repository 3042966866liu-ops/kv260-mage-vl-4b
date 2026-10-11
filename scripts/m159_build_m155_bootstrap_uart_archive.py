#!/usr/bin/env python3
"""Build a clean deterministic M155 bootstrap archive for COM3 transfer."""

from __future__ import annotations

import gzip
import hashlib
import json
import os
import shutil
import tarfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PACKAGE = ROOT / "tmp/m159_uart/m155_bootstrap_package"
TOP = "m155_bootstrap"
ARCHIVE = ROOT / "tmp/m159_uart/m155_bootstrap.tar.gz"
RESULT = ROOT / "deployment/mage_vl4b/M159_M155_BOOTSTRAP_UART_ARCHIVE_RESULT.json"
M140_SHA = "60bc5dad7f3609c32b4698ebbb372eba9a3ab9e74b273969dd322299b4431cbb"
SOURCES = {
    "m155_m120_usb_board_import.py": ROOT / "scripts/m155_m120_usb_board_import.py",
    "m155_run_m120_usb_board_import.sh": ROOT / "scripts/m155_run_m120_usb_board_import.sh",
    "M140_M120_SINGLE_CHAIN_BOARD_RESULT_01.json": ROOT / "deployment/mage_vl4b/M140_M120_SINGLE_CHAIN_BOARD_RESULT_01.json",
}


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def main() -> int:
    if PACKAGE.exists() or ARCHIVE.exists():
        raise RuntimeError("M159 requires absent clean package/archive paths")
    if sha256(SOURCES["M140_M120_SINGLE_CHAIN_BOARD_RESULT_01.json"]) != M140_SHA:
        raise RuntimeError("M159 M140 formal-result identity drift")
    temporary = PACKAGE.with_name(PACKAGE.name + f".partial-{os.getpid()}")
    temporary.mkdir(parents=True)
    entries: list[dict[str, object]] = []
    try:
        for relative, source in SOURCES.items():
            if not source.is_file() or source.is_symlink():
                raise RuntimeError(f"invalid M159 source: {source}")
            destination = temporary / relative
            shutil.copyfile(source, destination)
            entries.append({"path": relative, "bytes": destination.stat().st_size, "sha256": sha256(destination)})
        manifest = {
            "date": "2026-09-01",
            "gate": "M159-M155-bootstrap-package",
            "status": "PASS",
            "classification": "Clean M155 control bootstrap only; no USB write, board import, overlay or FPGA transaction.",
            "candidate_build_id": "0x4D395832",
            "m140_formal_result_sha256": M140_SHA,
            "files": entries,
            "file_count": len(entries),
        }
        (temporary / "PACKAGE_MANIFEST.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
        os.replace(temporary, PACKAGE)
    except BaseException:
        if temporary.exists():
            shutil.rmtree(temporary)
        raise
    actual = {path.relative_to(PACKAGE).as_posix() for path in PACKAGE.rglob("*") if path.is_file()}
    expected = {"PACKAGE_MANIFEST.json", *SOURCES.keys()}
    if actual != expected:
        raise RuntimeError("M159 clean package closure mismatch")
    manifest_sha = sha256(PACKAGE / "PACKAGE_MANIFEST.json")
    with ARCHIVE.open("xb") as raw:
        with gzip.GzipFile(filename="", mode="wb", fileobj=raw, mtime=0, compresslevel=9) as compressed:
            with tarfile.open(fileobj=compressed, mode="w") as archive:
                for relative in sorted(actual):
                    source = PACKAGE / relative
                    info = tarfile.TarInfo(f"{TOP}/{relative}")
                    info.size = source.stat().st_size
                    info.mode = 0o755 if relative.endswith((".py", ".sh")) else 0o644
                    info.mtime = 0
                    info.uid = info.gid = 0
                    info.uname = info.gname = ""
                    with source.open("rb") as stream:
                        archive.addfile(info, stream)
    result = {
        "date": "2026-09-01",
        "gate": "M159-M155-bootstrap-UART-archive",
        "status": "PASS",
        "classification": "Deterministic verified M155 control-bootstrap archive only; no COM3 transfer or board action.",
        "candidate_build_id": "0x4D395832",
        "package": PACKAGE.relative_to(ROOT).as_posix(),
        "package_manifest_sha256": manifest_sha,
        "archive": ARCHIVE.relative_to(ROOT).as_posix(),
        "archive_bytes": ARCHIVE.stat().st_size,
        "archive_sha256": sha256(ARCHIVE),
        "member_count": len(actual),
        "payload_file_count": len(entries),
        "board_state_changed": False,
    }
    RESULT.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, indent=2))
    print("M159_M155_BOOTSTRAP_UART_ARCHIVE_PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
