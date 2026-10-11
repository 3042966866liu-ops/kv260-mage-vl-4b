#!/usr/bin/env python3
"""Download, hash-verify and atomically import M120 weights on KV260."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import time
import urllib.request
from pathlib import Path, PurePosixPath


EXPECTED_BUILD = "0x4d395832"
EXPECTED_M140_SHA = "60bc5dad7f3609c32b4698ebbb372eba9a3ab9e74b273969dd322299b4431cbb"
EXPECTED_LANGUAGE = "12ea4b8cc58639d0aab6da4ef3a3f12bbbb1254f88865f76512a5f0d00d4ae5d"
EXPECTED_HEAD = "a1a555700e3daec8049627564c73e5783affe3827ab5437665249786d5c079ef"
EXPECTED_BYTES = 2_035_472_384
EXPECTED_FILES = 10
DESTINATION_NAME = "m120_fulltext_weights_0x4D395832"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(32 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def atomic_json(path: Path, value: dict) -> None:
    temporary = path.with_name(path.name + f".partial-{os.getpid()}")
    temporary.write_text(json.dumps(value, indent=2) + "\n", encoding="utf-8")
    os.replace(temporary, path)


def get_json(url: str) -> tuple[dict, bytes]:
    with urllib.request.urlopen(url, timeout=30) as response:
        if response.status != 200:
            raise RuntimeError(f"HTTP status {response.status}: {url}")
        payload = response.read()
    value = json.loads(payload)
    if not isinstance(value, dict):
        raise RuntimeError(f"JSON root mismatch: {url}")
    return value, payload


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-url", required=True)
    parser.add_argument("--destination", type=Path, required=True)
    parser.add_argument("--m140-result", type=Path, required=True)
    parser.add_argument("--result", type=Path, required=True)
    args = parser.parse_args()
    started = time.monotonic()
    result = {
        "date": "2026-09-01",
        "gate": "M162-M120-direct-Ethernet-board-import",
        "status": "FAIL",
        "classification": "Hash-verified full M120 weight import only; not Layer-0, fixed-text, full-model, performance, video or Web evidence.",
        "candidate_build_id": "0x4D395832",
    }
    staging: Path | None = None
    try:
        if os.geteuid() != 0:
            raise RuntimeError("M162 board import requires root")
        if args.base_url.rstrip("/") != "http://192.168.0.10:8765/tellme_m120_fulltext_0x4D395832":
            raise RuntimeError("M162 base URL identity mismatch")
        m140 = json.loads(args.m140_result.read_text(encoding="utf-8"))
        if sha256(args.m140_result) != EXPECTED_M140_SHA or m140.get("status") != "PASS" or m140.get("gate") != "M140-M120-COM3-single-chain":
            raise RuntimeError("M162 exact M140 predecessor mismatch")
        destination = args.destination.resolve()
        allowed_parent = Path("/home/ubuntu/tellme_m120_m89x2_20260901").resolve()
        if destination.parent != allowed_parent or destination.name != DESTINATION_NAME:
            raise RuntimeError(f"unsafe M162 destination: {destination}")
        staging = destination.with_name(destination.name + ".network-partial")
        if destination.exists() or staging.exists():
            raise RuntimeError("M162 requires absent destination and staging paths")
        ready, _ = get_json(args.base_url.rstrip("/") + "/NETWORK_READY.json")
        manifest, manifest_bytes = get_json(args.base_url.rstrip("/") + "/NETWORK_PAYLOAD_MANIFEST.json")
        manifest_sha = hashlib.sha256(manifest_bytes).hexdigest()
        if ready.get("status") != "READY" or ready.get("network_payload_manifest_sha256") != manifest_sha:
            raise RuntimeError("M162 network ready/manifest mismatch")
        if manifest.get("gate") != "M162-M120-direct-Ethernet-payload" or manifest.get("status") != "PASS":
            raise RuntimeError("M162 payload manifest status mismatch")
        if str(manifest.get("candidate_build_id", "")).lower() != EXPECTED_BUILD or manifest.get("m140_result_sha256") != EXPECTED_M140_SHA:
            raise RuntimeError("M162 payload build/predecessor mismatch")
        if manifest.get("language_manifest_sha256") != EXPECTED_LANGUAGE or manifest.get("lm_head_manifest_sha256") != EXPECTED_HEAD:
            raise RuntimeError("M162 payload layout mismatch")
        if int(manifest.get("payload_bytes", -1)) != EXPECTED_BYTES:
            raise RuntimeError("M162 payload byte count mismatch")
        entries = manifest.get("files")
        if not isinstance(entries, list) or len(entries) != EXPECTED_FILES:
            raise RuntimeError("M162 payload file count mismatch")
        free_before = int(shutil.disk_usage(destination.parent).free)
        if free_before < EXPECTED_BYTES + (128 << 20):
            raise RuntimeError(f"insufficient board free bytes: {free_before}")
        staging.mkdir(parents=True)
        copied = []
        payload_bytes = 0
        for entry in entries:
            relative = str(entry.get("path", ""))
            parts = PurePosixPath(relative).parts
            if not parts or parts[0] not in {"language_fourport", "lmhead_fourport"} or ".." in parts:
                raise RuntimeError(f"unsafe M162 member: {relative}")
            target = staging / Path(*parts)
            target.parent.mkdir(parents=True, exist_ok=True)
            partial = target.with_name(target.name + ".partial")
            digest = hashlib.sha256()
            observed_bytes = 0
            with urllib.request.urlopen(args.base_url.rstrip("/") + "/" + relative, timeout=60) as response, partial.open("xb") as output:
                if response.status != 200:
                    raise RuntimeError(f"HTTP status {response.status}: {relative}")
                for block in iter(lambda: response.read(4 << 20), b""):
                    digest.update(block)
                    observed_bytes += len(block)
                    output.write(block)
                output.flush()
                os.fsync(output.fileno())
            expected_bytes = int(entry.get("bytes", -1))
            if observed_bytes != expected_bytes or digest.hexdigest() != entry.get("sha256") or sha256(partial) != entry.get("sha256"):
                raise RuntimeError(f"M162 downloaded member mismatch: {relative}")
            os.replace(partial, target)
            copied.append({"path": relative, "bytes": observed_bytes, "sha256": entry["sha256"]})
            if entry.get("payload") is True:
                payload_bytes += observed_bytes
            print(f"M162_DOWNLOAD_MEMBER_PASS path={relative} bytes={observed_bytes}", flush=True)
        if payload_bytes != EXPECTED_BYTES:
            raise RuntimeError("M162 downloaded binary total mismatch")
        (staging / "NETWORK_PAYLOAD_MANIFEST.json").write_bytes(manifest_bytes)
        atomic_json(staging / "BOARD_IMPORT_MANIFEST.json", {
            "status": "PASS",
            "candidate_build_id": "0x4D395832",
            "transport": "direct-Ethernet-readonly-HTTP",
            "m140_result_sha256": EXPECTED_M140_SHA,
            "network_payload_manifest_sha256": manifest_sha,
            "files": copied,
            "file_count": len(copied),
            "payload_bytes": payload_bytes,
        })
        board_manifest_sha = sha256(staging / "BOARD_IMPORT_MANIFEST.json")
        atomic_json(staging / "BOARD_IMPORT_READY.json", {
            "status": "READY",
            "candidate_build_id": "0x4D395832",
            "board_import_manifest_sha256": board_manifest_sha,
        })
        os.replace(staging, destination)
        staging = None
        result.update({
            "status": "PASS",
            "transport": "direct-Ethernet-readonly-HTTP",
            "destination": str(destination),
            "m140_result_sha256": EXPECTED_M140_SHA,
            "network_payload_manifest_sha256": manifest_sha,
            "board_import_manifest_sha256": board_manifest_sha,
            "file_count": len(copied),
            "payload_bytes": payload_bytes,
            "free_bytes_before": free_before,
            "boot_dtb_cma_partitions_services_changed": False,
            "stable_rollback_preserved": True,
            "next_gate": "Transfer M154 over COM3 and execute only the M145 Layer-0 gate.",
        })
    except BaseException as error:
        result["error"] = f"{type(error).__name__}: {error}"
        result["next_gate"] = "Repair and rerun M162 network import only; do not execute Layer-0."
    finally:
        result["total_ms"] = (time.monotonic() - started) * 1000.0
        atomic_json(args.result.resolve(), result)
    print("__M162_NETWORK_IMPORT_RESULT_BEGIN__", flush=True)
    print(json.dumps(result, separators=(",", ":")), flush=True)
    print("__M162_NETWORK_IMPORT_RESULT_END__", flush=True)
    print("M162_M120_NETWORK_BOARD_IMPORT_PASS" if result["status"] == "PASS" else "M162_M120_NETWORK_BOARD_IMPORT_FAIL", flush=True)
    return 0 if result["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
