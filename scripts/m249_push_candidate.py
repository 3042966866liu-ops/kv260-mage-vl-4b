#!/usr/bin/env python3
"""Push the exact M249 package over a direct Ethernet connection."""

from __future__ import annotations

import argparse
import hashlib
import json
import socket
import struct
import time
from pathlib import Path


MAGIC = b"TELLME_M249_V1\n"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(4 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def receive_exact(stream: socket.socket, count: int) -> bytes:
    value = bytearray(count)
    view = memoryview(value)
    offset = 0
    while offset < count:
        observed = stream.recv_into(view[offset:], count - offset)
        if observed == 0:
            raise RuntimeError("unexpected EOF from board")
        offset += observed
    return bytes(value)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--candidate", type=Path, required=True)
    parser.add_argument("--expected-manifest-sha256", required=True)
    parser.add_argument("--host", default="192.168.0.2")
    parser.add_argument("--port", type=int, default=8769)
    parser.add_argument("--result", type=Path, required=True)
    args = parser.parse_args()
    started = time.monotonic()
    candidate = args.candidate.resolve()
    package_manifest = candidate / "PACKAGE_MANIFEST.json"
    if sha256(package_manifest) != args.expected_manifest_sha256:
        raise RuntimeError("local package manifest hash mismatch")
    files = sorted(path for path in candidate.rglob("*") if path.is_file())
    entries = [
        {"path": path.relative_to(candidate).as_posix(), "bytes": path.stat().st_size, "sha256": sha256(path)}
        for path in files
    ]
    transport = {
        "gate": "M249-KV260-SSDLite-direct-Ethernet-payload",
        "status": "PASS",
        "package_manifest_sha256": args.expected_manifest_sha256,
        "file_count": len(entries),
        "total_bytes": sum(item["bytes"] for item in entries),
        "files": entries,
    }
    payload = json.dumps(transport, separators=(",", ":")).encode("utf-8")
    with socket.create_connection((args.host, args.port), timeout=30) as connection:
        connection.settimeout(1800)
        connection.sendall(MAGIC)
        connection.sendall(struct.pack("!I", len(payload)))
        connection.sendall(payload)
        for item, path in zip(entries, files):
            name = item["path"].encode("utf-8")
            connection.sendall(struct.pack("!H", len(name)))
            connection.sendall(name)
            connection.sendall(struct.pack("!Q", item["bytes"]))
            with path.open("rb") as handle:
                for block in iter(lambda: handle.read(4 << 20), b""):
                    connection.sendall(block)
        connection.sendall(b"\x00\x00")
        response_size = struct.unpack("!I", receive_exact(connection, 4))[0]
        response = json.loads(receive_exact(connection, response_size))
    result = {
        "date": "2026-09-02",
        "gate": "M249-PC-outbound-direct-Ethernet-push",
        "status": "PASS" if response.get("status") == "PASS" else "FAIL",
        "classification": "Candidate transfer evidence only; not board detector, accuracy, action, Web, FPGA or real-time PASS.",
        "package_manifest_sha256": args.expected_manifest_sha256,
        "file_count": len(entries),
        "total_bytes": transport["total_bytes"],
        "response": response,
        "total_ms": (time.monotonic() - started) * 1000.0,
    }
    args.result.parent.mkdir(parents=True, exist_ok=True)
    args.result.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, indent=2))
    print("M249_PC_PUSH_PASS" if result["status"] == "PASS" else "M249_PC_PUSH_FAIL")
    return 0 if result["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
