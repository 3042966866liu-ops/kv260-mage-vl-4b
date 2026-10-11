#!/usr/bin/env python3
"""Stage the exact M120 language/head payload to one clean removable drive.

The writer is deliberately locked behind the real M140 single-chain PASS.  It
copies from the explicitly named Ubuntu-24.04 WSL distribution, verifies every
source and destination hash, then atomically promotes the staging directory.
"""

from __future__ import annotations

import argparse
import ctypes
import hashlib
import json
import os
import shutil
from datetime import datetime
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
EXPECTED_BUILD_ID = "0x4d395832"
EXPECTED_SMALL_PACKAGE = "7600ba1af87680fe1294ae6dc88f8e0968f23b2e38ca48dbfd316e351ea76e3e"
EXPECTED_LANGUAGE_MANIFEST = "12ea4b8cc58639d0aab6da4ef3a3f12bbbb1254f88865f76512a5f0d00d4ae5d"
EXPECTED_HEAD_MANIFEST = "a1a555700e3daec8049627564c73e5783affe3827ab5437665249786d5c079ef"
EXPECTED_PAYLOAD_BYTES = 2_035_472_384
EXPECTED_FREE_BYTES = 2_102_581_248
TARGET_NAME = "tellme_m120_fulltext_0x4D395832"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(32 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def checked_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise RuntimeError(f"JSON root is not an object: {path}")
    return value


def require_m140(path: Path) -> tuple[dict[str, Any], str]:
    if not path.is_file():
        raise RuntimeError("M150_LOCKED_UNTIL_M140_SINGLE_CHAIN_BOARD_PASS")
    value = checked_json(path)
    if value.get("gate") != "M140-M120-COM3-single-chain":
        raise RuntimeError("M140 gate identity mismatch")
    if value.get("status") != "PASS":
        raise RuntimeError("M150_LOCKED_UNTIL_M140_SINGLE_CHAIN_BOARD_PASS")
    if str(value.get("candidate_build_id", "")).lower() != EXPECTED_BUILD_ID:
        raise RuntimeError("M140 Build ID mismatch")
    if value.get("package_manifest_sha256") != EXPECTED_SMALL_PACKAGE:
        raise RuntimeError("M140 package identity mismatch")
    if value.get("fpga_transaction_executed") is not True:
        raise RuntimeError("M140 PASS lacks a real FPGA transaction")
    if value.get("stable_rollback_preserved") is not True:
        raise RuntimeError("M140 PASS does not preserve stable rollback")
    return value, sha256(path)


def require_m141(path: Path) -> tuple[dict[str, Any], str]:
    value = checked_json(path)
    if value.get("gate") != "M141-M120-fulltext-USB-source-audit" or value.get("status") != "PASS":
        raise RuntimeError("M141 source audit is not PASS")
    if value.get("language", {}).get("manifest_sha256") != EXPECTED_LANGUAGE_MANIFEST:
        raise RuntimeError("M141 language manifest identity mismatch")
    if value.get("lm_head", {}).get("manifest_sha256") != EXPECTED_HEAD_MANIFEST:
        raise RuntimeError("M141 LM-head manifest identity mismatch")
    if int(value.get("payload_bytes", -1)) != EXPECTED_PAYLOAD_BYTES:
        raise RuntimeError("M141 payload byte count mismatch")
    if int(value.get("usb_required_free_bytes", -1)) != EXPECTED_FREE_BYTES:
        raise RuntimeError("M141 USB free-space contract mismatch")
    return value, sha256(path)


def wsl_unc(distro: str, linux_path: str) -> Path:
    if not linux_path.startswith("/") or ".." in Path(linux_path).parts:
        raise RuntimeError(f"unsafe absolute WSL source path: {linux_path!r}")
    tail = linux_path.lstrip("/").replace("/", "\\")
    return Path(f"\\\\wsl.localhost\\{distro}\\{tail}")


def removable_root(value: str) -> tuple[Path, str, int]:
    destination = Path(value).resolve()
    drive, tail = os.path.splitdrive(str(destination))
    if not drive or tail not in {"\\", "/"}:
        raise RuntimeError("destination must be an exact Windows drive root such as E:\\")
    drive_root = f"{drive}\\"
    if drive.upper() == ROOT.drive.upper():
        raise RuntimeError("workspace/system drive is prohibited as the USB destination")
    drive_type = int(ctypes.windll.kernel32.GetDriveTypeW(ctypes.c_wchar_p(drive_root)))
    if drive_type != 2:  # DRIVE_REMOVABLE
        raise RuntimeError(f"destination drive type is {drive_type}, expected DRIVE_REMOVABLE=2")
    free = int(shutil.disk_usage(drive_root).free)
    if free < EXPECTED_FREE_BYTES:
        raise RuntimeError(f"insufficient USB free bytes: observed={free} required={EXPECTED_FREE_BYTES}")
    return Path(drive_root), drive_type, free


def source_entries(audit: dict[str, Any], distro: str) -> list[dict[str, Any]]:
    entries: list[dict[str, Any]] = []
    for key, target in (("language", "language_fourport"), ("lm_head", "lmhead_fourport")):
        section = audit[key]
        source_root = wsl_unc(distro, str(section["root"]))
        entries.append(
            {
                "source": source_root / "SIXPORT_LAYOUT_MANIFEST.json",
                "relative": f"{target}/SIXPORT_LAYOUT_MANIFEST.json",
                "sha256": section["manifest_sha256"],
                "payload": False,
            }
        )
        for item in section["files"]:
            entries.append(
                {
                    "source": source_root / item["path"],
                    "relative": f"{target}/{item['path']}",
                    "sha256": item["sha256"],
                    "bytes": int(item["bytes"]),
                    "payload": True,
                }
            )
    if len(entries) != 10:
        raise RuntimeError("expected two manifests plus eight payload shards")
    return entries


def copy_verified(entry: dict[str, Any], staging: Path) -> dict[str, Any]:
    source = Path(entry["source"])
    if not source.is_file():
        raise RuntimeError(f"source file absent: {source}")
    if entry.get("bytes") is not None and source.stat().st_size != int(entry["bytes"]):
        raise RuntimeError(f"source byte count mismatch: {source}")

    target = staging / entry["relative"]
    target.parent.mkdir(parents=True, exist_ok=True)
    partial = target.with_name(target.name + ".partial")
    if target.exists() or partial.exists():
        raise RuntimeError(f"refusing to overwrite staging member: {target}")

    source_digest = hashlib.sha256()
    with source.open("rb") as incoming, partial.open("xb") as outgoing:
        for chunk in iter(lambda: incoming.read(32 << 20), b""):
            source_digest.update(chunk)
            outgoing.write(chunk)
        outgoing.flush()
        os.fsync(outgoing.fileno())
    observed_source = source_digest.hexdigest()
    if observed_source != entry["sha256"]:
        raise RuntimeError(f"source SHA-256 mismatch during copy: {source}")
    if sha256(partial) != entry["sha256"]:
        raise RuntimeError(f"destination SHA-256 mismatch after copy: {partial}")
    os.replace(partial, target)
    return {
        "path": entry["relative"],
        "bytes": target.stat().st_size,
        "sha256": entry["sha256"],
        "source": str(source),
    }


def atomic_json(path: Path, value: dict[str, Any]) -> None:
    temporary = path.with_name(path.name + ".partial")
    temporary.write_text(json.dumps(value, indent=2) + "\n", encoding="utf-8")
    with temporary.open("rb") as handle:
        os.fsync(handle.fileno())
    os.replace(temporary, path)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--destination-root", required=True)
    parser.add_argument("--distro", default="Ubuntu-24.04")
    parser.add_argument(
        "--m140-result",
        type=Path,
        default=ROOT / "deployment/mage_vl4b/M140_M120_SINGLE_CHAIN_BOARD_RESULT_01.json",
    )
    parser.add_argument(
        "--m141-audit",
        type=Path,
        default=ROOT / "deployment/mage_vl4b/M141_M120_FULLTEXT_USB_SOURCE_AUDIT_RESULT.json",
    )
    args = parser.parse_args()

    m140, m140_sha = require_m140(args.m140_result.resolve())
    audit, m141_sha = require_m141(args.m141_audit.resolve())
    if args.distro != "Ubuntu-24.04":
        raise RuntimeError("M150 requires the exact WSL distro name Ubuntu-24.04")
    drive_root, drive_type, free_before = removable_root(args.destination_root)

    staging = drive_root / f".{TARGET_NAME}.partial"
    final = drive_root / TARGET_NAME
    if staging.exists() or final.exists():
        raise RuntimeError(f"clean destination required; refusing existing path: {staging} or {final}")
    staging.mkdir()

    copied: list[dict[str, Any]] = []
    for entry in source_entries(audit, args.distro):
        copied.append(copy_verified(entry, staging))
    payload_bytes = sum(item["bytes"] for item in copied if item["path"].endswith(".bin"))
    if payload_bytes != EXPECTED_PAYLOAD_BYTES:
        raise RuntimeError("copied payload byte count mismatch")

    manifest = {
        "date": datetime.now().astimezone().isoformat(timespec="seconds"),
        "gate": "M150-M120-fulltext-USB-stage",
        "status": "PASS",
        "classification": "Exact removable-drive staging with independent destination rehash; not a board Layer-0, fixed-text, full-model, video, performance or Web PASS.",
        "candidate_build_id": "0x4D395832",
        "distro": args.distro,
        "m140_result_sha256": m140_sha,
        "m140_gate": m140["gate"],
        "m141_audit_sha256": m141_sha,
        "language_manifest_sha256": EXPECTED_LANGUAGE_MANIFEST,
        "lm_head_manifest_sha256": EXPECTED_HEAD_MANIFEST,
        "files": copied,
        "file_count": len(copied),
        "payload_bytes": payload_bytes,
        "drive_type": drive_type,
        "free_bytes_before": free_before,
        "board_state_changed": False,
        "next_gate": "Safely eject the USB drive, insert it into KV260, then use COM3 to mount read-only and reverify this manifest before M145 Layer-0.",
    }
    atomic_json(staging / "USB_PAYLOAD_MANIFEST.json", manifest)
    manifest_sha = sha256(staging / "USB_PAYLOAD_MANIFEST.json")
    atomic_json(
        staging / "USB_READY.json",
        {
            "status": "READY",
            "candidate_build_id": "0x4D395832",
            "usb_payload_manifest_sha256": manifest_sha,
            "file_count": len(copied),
            "payload_bytes": payload_bytes,
        },
    )
    os.replace(staging, final)
    print(
        json.dumps(
            {
                "gate": "M150-M120-fulltext-USB-stage",
                "status": "PASS",
                "destination": str(final),
                "usb_payload_manifest_sha256": manifest_sha,
                "payload_bytes": payload_bytes,
                "file_count": len(copied),
            },
            indent=2,
        )
    )
    print("M150_M120_FULLTEXT_USB_STAGE_PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
