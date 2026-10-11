#!/usr/bin/env python3
"""Receive and atomically verify the exact M181 video package."""

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


MAGIC = b"TELLME_M184_V1\n"
PACKAGE_SHA = "1596536bfe6865cb7eab5c038d8b4da8b666afc7cbd629ddc4559781727151d6"
M182_SHA = "da6c69cb91a3956def857616f16d45358dd909b90967e110ad7e3a451b7e4f50"
DESTINATION_NAME = "m181_m120_video_board_candidate"
EXPECTED_FILES = 50
ALLOWED_TOP = {"auxiliary", "fixtures", "ps_vision_payload", "static", "text_auxiliary", "text_runtime", "vision_layout"}


def sha256(path: Path) -> str:
    value = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(32 << 20), b""):
            value.update(block)
    return value.hexdigest()


def atomic_json(path: Path, value: dict) -> None:
    temporary = path.with_name(path.name + f".partial-{os.getpid()}")
    temporary.write_text(json.dumps(value, indent=2) + "\n", encoding="utf-8")
    os.replace(temporary, path)


def receive_exact(stream: socket.socket, count: int) -> bytes:
    value = bytearray(count)
    view = memoryview(value)
    offset = 0
    while offset < count:
        observed = stream.recv_into(view[offset:], count - offset)
        if observed == 0:
            raise RuntimeError(f"unexpected EOF at {offset}/{count}")
        offset += observed
    return bytes(value)


def send_json(stream: socket.socket, value: dict) -> None:
    payload = (json.dumps(value, separators=(",", ":")) + "\n").encode("utf-8")
    stream.sendall(struct.pack("!I", len(payload)) + payload)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--bind", default="192.168.0.2")
    parser.add_argument("--port", type=int, default=8767)
    parser.add_argument("--destination", type=Path, required=True)
    parser.add_argument("--m182-result", type=Path, required=True)
    parser.add_argument("--result", type=Path, required=True)
    args = parser.parse_args()
    started = time.monotonic()
    result = {
        "date": "2026-09-01",
        "gate": "M184-M181-video-direct-Ethernet-board-import",
        "status": "FAIL",
        "classification": "Hash-verified video package import only; not PS-vision, FPGA video E2E, performance or Web evidence.",
        "candidate_build_id": "0x4D395832",
    }
    connection = None
    staging = None
    try:
        if os.geteuid() != 0:
            raise RuntimeError("M184 board receiver requires root")
        m182 = json.loads(args.m182_result.read_text(encoding="utf-8"))
        if sha256(args.m182_result) != M182_SHA or m182.get("status") != "PASS_OFFLINE_VIDEO_CANDIDATE_BOARD_NOT_EXECUTED":
            raise RuntimeError("M184 exact M182 predecessor mismatch")
        destination = args.destination.resolve()
        parent = Path("/home/ubuntu/tellme_m120_m89x2_20260901").resolve()
        if destination.parent != parent or destination.name != DESTINATION_NAME:
            raise RuntimeError(f"unsafe M184 destination: {destination}")
        staging = destination.with_name(destination.name + ".push-partial")
        if destination.exists() or staging.exists():
            raise RuntimeError("M184 requires absent destination and staging paths")

        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as listener:
            listener.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            listener.bind((args.bind, args.port))
            listener.listen(1)
            listener.settimeout(180)
            print(f"M184_BOARD_RECEIVER_READY bind={args.bind} port={args.port}", flush=True)
            connection, peer = listener.accept()
        connection.settimeout(1800)
        if peer[0] != "192.168.0.10":
            raise RuntimeError(f"M184 unexpected peer: {peer[0]}")
        if receive_exact(connection, len(MAGIC)) != MAGIC:
            raise RuntimeError("M184 protocol magic mismatch")
        manifest_size = struct.unpack("!I", receive_exact(connection, 4))[0]
        if manifest_size <= 0 or manifest_size > (2 << 20):
            raise RuntimeError("M184 unsafe transport manifest size")
        manifest_bytes = receive_exact(connection, manifest_size)
        manifest = json.loads(manifest_bytes)
        if manifest.get("gate") != "M184-M181-video-direct-Ethernet-payload" or manifest.get("status") != "PASS":
            raise RuntimeError("M184 transport manifest gate mismatch")
        if str(manifest.get("candidate_build_id", "")).lower() != "0x4d395832":
            raise RuntimeError("M184 transport Build ID mismatch")
        if manifest.get("package_manifest_sha256") != PACKAGE_SHA or manifest.get("m182_result_sha256") != M182_SHA:
            raise RuntimeError("M184 transport package/predecessor mismatch")
        entries = manifest.get("files")
        if not isinstance(entries, list) or len(entries) != EXPECTED_FILES or int(manifest.get("file_count", -1)) != EXPECTED_FILES:
            raise RuntimeError("M184 transport file count mismatch")
        expected = {str(item.get("path", "")): item for item in entries}
        if len(expected) != EXPECTED_FILES:
            raise RuntimeError("M184 duplicate transport path")
        total_bytes = sum(int(item.get("bytes", -1)) for item in entries)
        if total_bytes != int(manifest.get("total_bytes", -1)):
            raise RuntimeError("M184 transport byte total mismatch")
        free_before = int(shutil.disk_usage(parent).free)
        if free_before < total_bytes + (128 << 20):
            raise RuntimeError(f"insufficient board free bytes: {free_before}")

        staging.mkdir(parents=True)
        copied = []
        for ordinal in range(EXPECTED_FILES):
            path_size = struct.unpack("!H", receive_exact(connection, 2))[0]
            if path_size <= 0 or path_size > 512:
                raise RuntimeError("M184 unsafe path size")
            relative = receive_exact(connection, path_size).decode("utf-8")
            size = struct.unpack("!Q", receive_exact(connection, 8))[0]
            item = expected.get(relative)
            if item is None or int(item.get("bytes", -1)) != size:
                raise RuntimeError(f"M184 member identity mismatch: {relative}")
            parts = PurePosixPath(relative).parts
            top_ok = len(parts) == 1 and relative in {"PACKAGE_MANIFEST.json", "PACKAGE_READY.json", "board_preprocess.py", "ps_vision_runtime.py", "test_board_preprocess.py", "test_ps_vision_runtime.py", "test_ps_vision_weight_decode.py", "test_video_prompt_and_splice.py", "test_video_request.py", "video_language_runtime.py", "video_prompt.py", "video_request.py", "video_server.py"}
            if not parts or ".." in parts or (parts[0] not in ALLOWED_TOP and not top_ok) or "__pycache__" in parts or relative.endswith(".pyc") or relative.endswith(".partial"):
                raise RuntimeError(f"unsafe M184 member: {relative}")
            target = staging.joinpath(*parts)
            target.parent.mkdir(parents=True, exist_ok=True)
            partial = target.with_name(target.name + ".partial")
            value = hashlib.sha256()
            remaining = size
            with partial.open("xb") as output:
                while remaining:
                    block = connection.recv(min(4 << 20, remaining))
                    if not block:
                        raise RuntimeError(f"unexpected EOF in {relative}")
                    output.write(block)
                    value.update(block)
                    remaining -= len(block)
                output.flush()
                os.fsync(output.fileno())
            if value.hexdigest() != item.get("sha256") or sha256(partial) != item.get("sha256"):
                raise RuntimeError(f"M184 received member hash mismatch: {relative}")
            os.replace(partial, target)
            copied.append(relative)
            print(f"M184_RECEIVE_MEMBER_PASS ordinal={ordinal+1}/{EXPECTED_FILES} path={relative} bytes={size}", flush=True)
        if receive_exact(connection, 2) != b"\x00\x00" or set(copied) != set(expected):
            raise RuntimeError("M184 received closure mismatch")
        package_path = staging / "PACKAGE_MANIFEST.json"
        if sha256(package_path) != PACKAGE_SHA:
            raise RuntimeError("M184 nested package manifest mismatch")
        package = json.loads(package_path.read_text(encoding="utf-8"))
        declared = {item["path"]: item for item in package["files"]}
        if len(declared) != 48:
            raise RuntimeError("M184 nested package file count mismatch")
        for relative, item in declared.items():
            path = staging / relative
            if not path.is_file() or path.stat().st_size != int(item["bytes"]) or sha256(path) != item["sha256"]:
                raise RuntimeError(f"M184 nested package member mismatch: {relative}")
        ready = json.loads((staging / "PACKAGE_READY.json").read_text(encoding="utf-8"))
        if ready.get("status") != "READY" or ready.get("package_manifest_sha256") != PACKAGE_SHA:
            raise RuntimeError("M184 nested PACKAGE_READY mismatch")
        os.replace(staging, destination)
        staging = None
        result.update({
            "status": "PASS",
            "transport": "direct-Ethernet-PC-outbound-push",
            "destination": str(destination),
            "peer": peer[0],
            "package_manifest_sha256": PACKAGE_SHA,
            "m182_result_sha256": M182_SHA,
            "file_count": EXPECTED_FILES,
            "total_bytes": total_bytes,
            "free_bytes_before": free_before,
            "boot_dtb_cma_partitions_services_changed": False,
            "stable_rollback_preserved": True,
            "next_gate": "Run only the fixed four-frame PS-vision board numerical gate.",
        })
        send_json(connection, {"status": "PASS", "package_manifest_sha256": PACKAGE_SHA, "total_bytes": total_bytes})
    except BaseException as error:
        result["error"] = f"{type(error).__name__}: {error}"
        result["next_gate"] = "Repair and rerun only M184 transfer; do not execute video inference."
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
    print("__M184_VIDEO_IMPORT_RESULT_BEGIN__", flush=True)
    print(json.dumps(result, separators=(",", ":")), flush=True)
    print("__M184_VIDEO_IMPORT_RESULT_END__", flush=True)
    print("M184_M181_VIDEO_BOARD_IMPORT_PASS" if result["status"] == "PASS" else "M184_M181_VIDEO_BOARD_IMPORT_FAIL", flush=True)
    return 0 if result["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
