#!/usr/bin/env python3
"""Verify a read-only M150 USB payload and atomically import it on KV260."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import time
from pathlib import Path, PurePosixPath
from typing import Any


EXPECTED_BUILD_ID = "0x4d395832"
EXPECTED_SMALL_PACKAGE = "7600ba1af87680fe1294ae6dc88f8e0968f23b2e38ca48dbfd316e351ea76e3e"
EXPECTED_LANGUAGE_MANIFEST = "12ea4b8cc58639d0aab6da4ef3a3f12bbbb1254f88865f76512a5f0d00d4ae5d"
EXPECTED_HEAD_MANIFEST = "a1a555700e3daec8049627564c73e5783affe3827ab5437665249786d5c079ef"
EXPECTED_PAYLOAD_BYTES = 2_035_472_384
EXPECTED_FILE_COUNT = 10
USB_DIRECTORY = "tellme_m120_fulltext_0x4D395832"
DESTINATION_NAME = "m120_fulltext_weights_0x4D395832"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(32 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def checked_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise RuntimeError(f"JSON root is not an object: {path}")
    return value


def atomic_json(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + f".partial-{os.getpid()}")
    temporary.write_text(json.dumps(value, indent=2) + "\n", encoding="utf-8")
    os.replace(temporary, path)


def require_read_only_mount(path: Path) -> str:
    resolved = path.resolve()
    candidates: list[tuple[int, str, set[str]]] = []
    for line in Path("/proc/self/mountinfo").read_text(encoding="utf-8").splitlines():
        fields = line.split()
        if len(fields) < 10 or "-" not in fields:
            continue
        mountpoint = Path(fields[4].replace("\\040", " ")).resolve()
        try:
            resolved.relative_to(mountpoint)
        except ValueError:
            continue
        candidates.append((len(mountpoint.parts), str(mountpoint), set(fields[5].split(","))))
    if not candidates:
        raise RuntimeError("USB source is not below a mounted filesystem")
    _, mountpoint, options = max(candidates)
    if "ro" not in options:
        raise RuntimeError(f"USB source mount is not read-only: {mountpoint}")
    return mountpoint


def verify_m140(path: Path) -> tuple[dict[str, Any], str]:
    value = checked_json(path)
    if value.get("gate") != "M140-M120-COM3-single-chain" or value.get("status") != "PASS":
        raise RuntimeError("M155 requires exact M140 single-chain PASS")
    if str(value.get("candidate_build_id", "")).lower() != EXPECTED_BUILD_ID:
        raise RuntimeError("M140 Build ID mismatch")
    if value.get("package_manifest_sha256") != EXPECTED_SMALL_PACKAGE:
        raise RuntimeError("M140 package identity mismatch")
    if value.get("fpga_transaction_executed") is not True:
        raise RuntimeError("M140 does not prove a real FPGA transaction")
    if value.get("stable_rollback_preserved") is not True:
        raise RuntimeError("M140 stable rollback evidence missing")
    return value, sha256(path)


def validate_source(source: Path, m140_sha: str) -> tuple[dict[str, Any], list[dict[str, Any]], str]:
    if source.name != USB_DIRECTORY:
        raise RuntimeError(f"unexpected M150 USB directory name: {source}")
    ready = checked_json(source / "USB_READY.json")
    if ready.get("status") != "READY" or str(ready.get("candidate_build_id", "")).lower() != EXPECTED_BUILD_ID:
        raise RuntimeError("M150 USB ready identity mismatch")
    manifest_path = source / "USB_PAYLOAD_MANIFEST.json"
    manifest_sha = sha256(manifest_path)
    if ready.get("usb_payload_manifest_sha256") != manifest_sha:
        raise RuntimeError("M150 USB payload manifest hash mismatch")
    manifest = checked_json(manifest_path)
    if manifest.get("gate") != "M150-M120-fulltext-USB-stage" or manifest.get("status") != "PASS":
        raise RuntimeError("M150 USB payload status mismatch")
    if str(manifest.get("candidate_build_id", "")).lower() != EXPECTED_BUILD_ID:
        raise RuntimeError("M150 USB Build ID mismatch")
    if manifest.get("m140_result_sha256") != m140_sha:
        raise RuntimeError("M150 USB payload was not unlocked by this exact M140 result")
    if manifest.get("language_manifest_sha256") != EXPECTED_LANGUAGE_MANIFEST:
        raise RuntimeError("M150 language manifest identity mismatch")
    if manifest.get("lm_head_manifest_sha256") != EXPECTED_HEAD_MANIFEST:
        raise RuntimeError("M150 LM-head manifest identity mismatch")
    if int(manifest.get("payload_bytes", -1)) != EXPECTED_PAYLOAD_BYTES:
        raise RuntimeError("M150 USB payload byte count mismatch")
    entries = manifest.get("files")
    if not isinstance(entries, list) or len(entries) != EXPECTED_FILE_COUNT:
        raise RuntimeError("M150 USB file-count mismatch")
    seen: set[str] = set()
    payload_bytes = 0
    for entry in entries:
        relative = str(entry.get("path", ""))
        parts = PurePosixPath(relative).parts
        if not parts or parts[0] not in {"language_fourport", "lmhead_fourport"} or ".." in parts:
            raise RuntimeError(f"unsafe M150 USB member: {relative}")
        if relative in seen:
            raise RuntimeError(f"duplicate M150 USB member: {relative}")
        seen.add(relative)
        path = (source / Path(*parts)).resolve()
        if source.resolve() not in path.parents or not path.is_file() or path.is_symlink():
            raise RuntimeError(f"invalid M150 USB member: {relative}")
        expected_bytes = int(entry.get("bytes", -1))
        if path.stat().st_size != expected_bytes or sha256(path) != entry.get("sha256"):
            raise RuntimeError(f"M150 USB member mismatch: {relative}")
        if relative.endswith(".bin"):
            payload_bytes += expected_bytes
    if payload_bytes != EXPECTED_PAYLOAD_BYTES:
        raise RuntimeError("verified M150 USB binary byte count mismatch")
    return manifest, entries, manifest_sha


def copy_entry(source_root: Path, staging: Path, entry: dict[str, Any]) -> dict[str, Any]:
    relative = str(entry["path"])
    source = source_root / relative
    target = staging / relative
    target.parent.mkdir(parents=True, exist_ok=True)
    partial = target.with_name(target.name + ".partial")
    digest = hashlib.sha256()
    with source.open("rb") as incoming, partial.open("xb") as outgoing:
        for block in iter(lambda: incoming.read(32 << 20), b""):
            digest.update(block)
            outgoing.write(block)
        outgoing.flush()
        os.fsync(outgoing.fileno())
    if digest.hexdigest() != entry["sha256"] or sha256(partial) != entry["sha256"]:
        raise RuntimeError(f"board import hash mismatch: {relative}")
    os.replace(partial, target)
    return {"path": relative, "bytes": target.stat().st_size, "sha256": entry["sha256"]}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--usb-root", type=Path, required=True)
    parser.add_argument("--destination", type=Path, required=True)
    parser.add_argument("--m140-result", type=Path, required=True)
    parser.add_argument("--result", type=Path, required=True)
    args = parser.parse_args()
    started = time.monotonic()
    result: dict[str, Any] = {
        "date": "2026-09-01",
        "gate": "M155-M120-fulltext-USB-board-import",
        "status": "FAIL",
        "classification": "Hash-verified full M120 weight import only; not Layer-0, fixed-text, full-model, performance, video or Web evidence.",
        "candidate_build_id": "0x4D395832",
    }
    try:
        if os.geteuid() != 0:
            raise RuntimeError("M155 board import requires root")
        source = args.usb_root.resolve()
        destination = args.destination.resolve()
        home = Path("/home/ubuntu").resolve()
        if destination.name != DESTINATION_NAME or home not in destination.parents:
            raise RuntimeError(f"unsafe M155 destination: {destination}")
        staging = destination.with_name(destination.name + ".partial")
        if destination.exists() or staging.exists():
            raise RuntimeError("M155 requires an absent clean destination and staging path")
        mountpoint = require_read_only_mount(source)
        _, m140_sha = verify_m140(args.m140_result.resolve())
        _, entries, usb_manifest_sha = validate_source(source, m140_sha)
        free_before = int(shutil.disk_usage(destination.parent).free)
        if free_before < EXPECTED_PAYLOAD_BYTES + (128 << 20):
            raise RuntimeError(f"insufficient board free space: {free_before}")
        staging.mkdir(parents=True)
        copied = [copy_entry(source, staging, entry) for entry in entries]
        shutil.copy2(source / "USB_PAYLOAD_MANIFEST.json", staging / "USB_PAYLOAD_MANIFEST.json")
        shutil.copy2(source / "USB_READY.json", staging / "USB_READY.json")
        board_manifest = {
            "status": "PASS",
            "candidate_build_id": "0x4D395832",
            "m140_result_sha256": m140_sha,
            "usb_payload_manifest_sha256": usb_manifest_sha,
            "source_mountpoint": mountpoint,
            "files": copied,
            "file_count": len(copied),
            "payload_bytes": EXPECTED_PAYLOAD_BYTES,
        }
        atomic_json(staging / "BOARD_IMPORT_MANIFEST.json", board_manifest)
        board_manifest_sha = sha256(staging / "BOARD_IMPORT_MANIFEST.json")
        atomic_json(
            staging / "BOARD_IMPORT_READY.json",
            {
                "status": "READY",
                "candidate_build_id": "0x4D395832",
                "board_import_manifest_sha256": board_manifest_sha,
            },
        )
        os.replace(staging, destination)
        result.update(
            {
                "status": "PASS",
                "fpga_transaction_executed": False,
                "source_was_read_only": True,
                "source_mountpoint": mountpoint,
                "destination": str(destination),
                "m140_result_sha256": m140_sha,
                "usb_payload_manifest_sha256": usb_manifest_sha,
                "board_import_manifest_sha256": board_manifest_sha,
                "file_count": len(copied),
                "payload_bytes": EXPECTED_PAYLOAD_BYTES,
                "free_bytes_before": free_before,
                "boot_dtb_cma_partitions_services_changed": False,
                "stable_rollback_preserved": True,
                "next_gate": "Run M154 package stage, then execute M145 complete Layer-0 only.",
            }
        )
    except BaseException as error:
        result["error"] = f"{type(error).__name__}: {error}"
        result["next_gate"] = "Repair and rerun M155 import only; do not execute Layer-0."
    result["total_ms"] = (time.monotonic() - started) * 1000.0
    atomic_json(args.result.resolve(), result)
    print(json.dumps(result, indent=2), flush=True)
    print("M155_M120_USB_BOARD_IMPORT_PASS" if result["status"] == "PASS" else "M155_M120_USB_BOARD_IMPORT_FAIL")
    return 0 if result["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
