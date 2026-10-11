#!/usr/bin/env python3
"""Receive the exact M120 payload from a Windows outbound TCP client."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import socket
import struct
import time
from pathlib import Path, PurePosixPath


MAGIC = b"TELLME_M163_V1\n"
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


def receive_exact(stream: socket.socket, count: int) -> bytes:
    chunks = bytearray(count)
    view = memoryview(chunks)
    offset = 0
    while offset < count:
        observed = stream.recv_into(view[offset:], count - offset)
        if observed == 0:
            raise RuntimeError(f"unexpected EOF at {offset}/{count}")
        offset += observed
    return bytes(chunks)


def send_json(stream: socket.socket, value: dict) -> None:
    payload = (json.dumps(value, separators=(",", ":")) + "\n").encode("utf-8")
    stream.sendall(struct.pack("!I", len(payload)) + payload)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--bind", default="192.168.0.2")
    parser.add_argument("--port", type=int, default=8766)
    parser.add_argument("--destination", type=Path, required=True)
    parser.add_argument("--m140-result", type=Path, required=True)
    parser.add_argument("--result", type=Path, required=True)
    args = parser.parse_args()
    started = time.monotonic()
    result = {
        "date": "2026-09-01",
        "gate": "M163-M120-direct-Ethernet-PC-push-board-import",
        "status": "FAIL",
        "classification": "Hash-verified complete M120 weight import only; not Layer-0, fixed-text, full-model, performance, video or Web evidence.",
        "candidate_build_id": "0x4D395832",
    }
    connection: socket.socket | None = None
    staging: Path | None = None
    try:
        if os.geteuid() != 0:
            raise RuntimeError("M163 board receiver requires root")
        m140 = json.loads(args.m140_result.read_text(encoding="utf-8"))
        if sha256(args.m140_result) != EXPECTED_M140_SHA or m140.get("status") != "PASS" or m140.get("gate") != "M140-M120-COM3-single-chain":
            raise RuntimeError("M163 exact M140 predecessor mismatch")
        destination = args.destination.resolve()
        allowed_parent = Path("/home/ubuntu/tellme_m120_m89x2_20260901").resolve()
        if destination.parent != allowed_parent or destination.name != DESTINATION_NAME:
            raise RuntimeError(f"unsafe M163 destination: {destination}")
        staging = destination.with_name(destination.name + ".push-partial")
        if destination.exists() or staging.exists():
            raise RuntimeError("M163 requires absent destination and staging paths")
        free_before = int(shutil.disk_usage(destination.parent).free)
        if free_before < EXPECTED_BYTES + (128 << 20):
            raise RuntimeError(f"insufficient board free bytes: {free_before}")

        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as listener:
            listener.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            listener.bind((args.bind, args.port))
            listener.listen(1)
            listener.settimeout(180)
            print(f"M163_BOARD_RECEIVER_READY bind={args.bind} port={args.port}", flush=True)
            connection, peer = listener.accept()
        connection.settimeout(600)
        if peer[0] != "192.168.0.10":
            raise RuntimeError(f"M163 unexpected peer: {peer[0]}")
        if receive_exact(connection, len(MAGIC)) != MAGIC:
            raise RuntimeError("M163 protocol magic mismatch")
        manifest_size = struct.unpack("!I", receive_exact(connection, 4))[0]
        if manifest_size <= 0 or manifest_size > (4 << 20):
            raise RuntimeError(f"M163 unsafe manifest size: {manifest_size}")
        manifest_bytes = receive_exact(connection, manifest_size)
        manifest = json.loads(manifest_bytes)
        manifest_sha = hashlib.sha256(manifest_bytes).hexdigest()
        if manifest.get("gate") != "M162-M120-direct-Ethernet-payload" or manifest.get("status") != "PASS":
            raise RuntimeError("M163 payload manifest status mismatch")
        if str(manifest.get("candidate_build_id", "")).lower() != EXPECTED_BUILD or manifest.get("m140_result_sha256") != EXPECTED_M140_SHA:
            raise RuntimeError("M163 payload identity mismatch")
        if manifest.get("language_manifest_sha256") != EXPECTED_LANGUAGE or manifest.get("lm_head_manifest_sha256") != EXPECTED_HEAD:
            raise RuntimeError("M163 layout identity mismatch")
        if int(manifest.get("payload_bytes", -1)) != EXPECTED_BYTES:
            raise RuntimeError("M163 payload byte count mismatch")
        entries = manifest.get("files")
        if not isinstance(entries, list) or len(entries) != EXPECTED_FILES:
            raise RuntimeError("M163 payload file count mismatch")
        expected_by_path = {str(item.get("path", "")): item for item in entries}
        if len(expected_by_path) != EXPECTED_FILES:
            raise RuntimeError("M163 duplicate manifest path")

        staging.mkdir(parents=True)
        copied: list[dict] = []
        payload_bytes = 0
        for ordinal in range(EXPECTED_FILES):
            path_size = struct.unpack("!H", receive_exact(connection, 2))[0]
            if path_size <= 0 or path_size > 512:
                raise RuntimeError(f"M163 unsafe path size: {path_size}")
            relative = receive_exact(connection, path_size).decode("utf-8")
            size = struct.unpack("!Q", receive_exact(connection, 8))[0]
            expected = expected_by_path.get(relative)
            if expected is None or int(expected.get("bytes", -1)) != size:
                raise RuntimeError(f"M163 member identity mismatch: {relative}")
            parts = PurePosixPath(relative).parts
            if not parts or parts[0] not in {"language_fourport", "lmhead_fourport"} or ".." in parts:
                raise RuntimeError(f"unsafe M163 member: {relative}")
            target = staging / Path(*parts)
            target.parent.mkdir(parents=True, exist_ok=True)
            partial = target.with_name(target.name + ".partial")
            digest = hashlib.sha256()
            remaining = size
            with partial.open("xb") as output:
                while remaining:
                    block = connection.recv(min(4 << 20, remaining))
                    if not block:
                        raise RuntimeError(f"unexpected EOF in {relative}")
                    output.write(block)
                    digest.update(block)
                    remaining -= len(block)
                output.flush()
                os.fsync(output.fileno())
            if digest.hexdigest() != expected.get("sha256") or sha256(partial) != expected.get("sha256"):
                raise RuntimeError(f"M163 received member hash mismatch: {relative}")
            os.replace(partial, target)
            copied.append({"path": relative, "bytes": size, "sha256": expected["sha256"]})
            if expected.get("payload") is True:
                payload_bytes += size
            print(f"M163_RECEIVE_MEMBER_PASS ordinal={ordinal + 1}/{EXPECTED_FILES} path={relative} bytes={size}", flush=True)
        if receive_exact(connection, 2) != b"\x00\x00":
            raise RuntimeError("M163 final protocol marker mismatch")
        if set(item["path"] for item in copied) != set(expected_by_path) or payload_bytes != EXPECTED_BYTES:
            raise RuntimeError("M163 received closure mismatch")

        (staging / "NETWORK_PAYLOAD_MANIFEST.json").write_bytes(manifest_bytes)
        atomic_json(staging / "BOARD_IMPORT_MANIFEST.json", {
            "status": "PASS",
            "candidate_build_id": "0x4D395832",
            "transport": "direct-Ethernet-PC-outbound-push",
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
            "transport": "direct-Ethernet-PC-outbound-push",
            "destination": str(destination),
            "peer": peer[0],
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
        send_json(connection, {"status": "PASS", "payload_bytes": payload_bytes, "board_import_manifest_sha256": board_manifest_sha})
    except BaseException as error:
        result["error"] = f"{type(error).__name__}: {error}"
        result["next_gate"] = "Repair and rerun M163 transfer only; do not execute Layer-0."
        if connection is not None:
            try:
                send_json(connection, {"status": "FAIL", "error": result["error"]})
            except OSError:
                pass
    finally:
        if connection is not None:
            connection.close()
        result["total_ms"] = (time.monotonic() - started) * 1000.0
        atomic_json(args.result.resolve(), result)
    print("__M163_NETWORK_IMPORT_RESULT_BEGIN__", flush=True)
    print(json.dumps(result, separators=(",", ":")), flush=True)
    print("__M163_NETWORK_IMPORT_RESULT_END__", flush=True)
    print("M163_M120_BOARD_IMPORT_PASS" if result["status"] == "PASS" else "M163_M120_BOARD_IMPORT_FAIL", flush=True)
    return 0 if result["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
