#!/usr/bin/env python3
"""Receive and atomically verify the exact M249 board speed candidate."""

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


MAGIC = b"TELLME_M249_V1\n"
PACKAGE_SHA = "0b631d5bd50fa1eeec42d2340a7f8af2b773da4b2df06c8f5204cd1309ee6ea2"
DESTINATION_NAME = "m249_ssdlite_board_candidate"
EXPECTED_PAYLOAD_FILES = 10
EXPECTED_TRANSPORT_FILES = 12
ALLOWED_TOP = {"fixtures", "model", "runtime", "wheels"}
ALLOWED_ROOT = {
    "M249_PREDECESSOR_SUMMARY.json",
    "PACKAGE_MANIFEST.json",
    "PACKAGE_READY.json",
    "run_m249_board_gate.sh",
}


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(4 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def atomic_json(path: Path, value: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
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
    parser.add_argument("--port", type=int, default=8769)
    parser.add_argument("--destination", type=Path, required=True)
    parser.add_argument("--result", type=Path, required=True)
    args = parser.parse_args()
    started = time.monotonic()
    result = {
        "date": "2026-09-02",
        "gate": "M249-KV260-SSDLite-direct-Ethernet-import",
        "status": "FAIL",
        "classification": "Hash-verified candidate import only; not detector speed, accuracy, action, Web, FPGA or real-time evidence.",
        "boot_dtb_cma_partitions_services_changed": False,
        "stable_t32_overlay_preserved": True,
    }
    connection = None
    staging = None
    try:
        if os.geteuid() != 0:
            raise RuntimeError("M249 receiver requires root")
        destination = args.destination.resolve()
        parent = Path("/home/ubuntu/tellme_m120_m89x2_20260901").resolve()
        if destination.parent != parent or destination.name != DESTINATION_NAME:
            raise RuntimeError(f"unsafe destination: {destination}")
        staging = destination.with_name(destination.name + ".push-partial")
        if destination.exists() or staging.exists():
            raise RuntimeError("destination and staging must both be absent")

        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as listener:
            listener.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            listener.bind((args.bind, args.port))
            listener.listen(1)
            listener.settimeout(300)
            print(f"M249_BOARD_RECEIVER_READY bind={args.bind} port={args.port}", flush=True)
            connection, peer = listener.accept()
        connection.settimeout(1800)
        if peer[0] != "192.168.0.10" or receive_exact(connection, len(MAGIC)) != MAGIC:
            raise RuntimeError(f"peer/protocol mismatch: {peer}")
        manifest_size = struct.unpack("!I", receive_exact(connection, 4))[0]
        if manifest_size <= 0 or manifest_size > (2 << 20):
            raise RuntimeError("unsafe transport manifest size")
        transport = json.loads(receive_exact(connection, manifest_size))
        if transport.get("gate") != "M249-KV260-SSDLite-direct-Ethernet-payload" or transport.get("status") != "PASS":
            raise RuntimeError("transport identity mismatch")
        if transport.get("package_manifest_sha256") != PACKAGE_SHA:
            raise RuntimeError("transport package hash mismatch")
        entries = transport.get("files")
        if not isinstance(entries, list) or len(entries) != EXPECTED_TRANSPORT_FILES:
            raise RuntimeError("transport file count mismatch")
        expected = {str(item.get("path", "")): item for item in entries}
        if len(expected) != EXPECTED_TRANSPORT_FILES:
            raise RuntimeError("duplicate transport path")
        total_bytes = sum(int(item.get("bytes", -1)) for item in entries)
        if total_bytes != int(transport.get("total_bytes", -1)):
            raise RuntimeError("transport byte total mismatch")
        free_before = int(shutil.disk_usage(parent).free)
        if free_before < total_bytes + (128 << 20):
            raise RuntimeError(f"insufficient board free bytes: {free_before}")

        staging.mkdir(parents=True)
        copied = []
        for ordinal in range(EXPECTED_TRANSPORT_FILES):
            path_size = struct.unpack("!H", receive_exact(connection, 2))[0]
            if path_size <= 0 or path_size > 512:
                raise RuntimeError("unsafe path size")
            relative = receive_exact(connection, path_size).decode("utf-8")
            size = struct.unpack("!Q", receive_exact(connection, 8))[0]
            item = expected.get(relative)
            if item is None or int(item.get("bytes", -1)) != size:
                raise RuntimeError(f"member identity mismatch: {relative}")
            parts = PurePosixPath(relative).parts
            root_member = len(parts) == 1 and relative in ALLOWED_ROOT
            if not parts or ".." in parts or (parts[0] not in ALLOWED_TOP and not root_member):
                raise RuntimeError(f"unsafe member: {relative}")
            if "__pycache__" in parts or relative.endswith((".pyc", ".partial")):
                raise RuntimeError(f"cache/partial member forbidden: {relative}")
            target = staging.joinpath(*parts)
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
            if digest.hexdigest() != item.get("sha256") or sha256(partial) != item.get("sha256"):
                raise RuntimeError(f"member hash mismatch: {relative}")
            os.replace(partial, target)
            copied.append(relative)
            print(f"M249_RECEIVE_MEMBER_PASS ordinal={ordinal+1}/{EXPECTED_TRANSPORT_FILES} path={relative} bytes={size}", flush=True)
        if receive_exact(connection, 2) != b"\x00\x00" or set(copied) != set(expected):
            raise RuntimeError("transport closure mismatch")

        package_path = staging / "PACKAGE_MANIFEST.json"
        if sha256(package_path) != PACKAGE_SHA:
            raise RuntimeError("nested package manifest mismatch")
        package = json.loads(package_path.read_text(encoding="utf-8"))
        declared = {item["path"]: item for item in package["files"]}
        if len(declared) != EXPECTED_PAYLOAD_FILES:
            raise RuntimeError("nested package file count mismatch")
        for relative, item in declared.items():
            path = staging / relative
            if not path.is_file() or path.stat().st_size != int(item["bytes"]) or sha256(path) != item["sha256"]:
                raise RuntimeError(f"nested member mismatch: {relative}")
        ready = json.loads((staging / "PACKAGE_READY.json").read_text(encoding="utf-8"))
        if ready.get("status") != "READY" or ready.get("package_manifest_sha256") != PACKAGE_SHA:
            raise RuntimeError("PACKAGE_READY mismatch")
        os.replace(staging, destination)
        staging = None
        result.update({
            "status": "PASS",
            "transport": "direct-Ethernet-PC-outbound-push",
            "destination": str(destination),
            "peer": peer[0],
            "package_manifest_sha256": PACKAGE_SHA,
            "file_count": EXPECTED_TRANSPORT_FILES,
            "total_bytes": total_bytes,
            "free_bytes_before": free_before,
            "next_gate": "Run only the M249 fixed-frame A53 detector speed gate.",
        })
        send_json(connection, {"status": "PASS", "package_manifest_sha256": PACKAGE_SHA, "total_bytes": total_bytes})
    except BaseException as error:
        result["error"] = f"{type(error).__name__}: {error}"
        result["next_gate"] = "Repair and rerun only M249 import; do not run the detector gate."
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
    print("__M249_IMPORT_RESULT_BEGIN__", flush=True)
    print(json.dumps(result, separators=(",", ":")), flush=True)
    print("__M249_IMPORT_RESULT_END__", flush=True)
    print("M249_BOARD_IMPORT_PASS" if result["status"] == "PASS" else "M249_BOARD_IMPORT_FAIL", flush=True)
    return 0 if result["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
