#!/usr/bin/env python3
"""Push the exact M181 video package to the KV260 receiver."""

from __future__ import annotations

import argparse
import hashlib
import json
import socket
import struct
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CANDIDATE = ROOT / "deployment/mage_vl4b/m181_m120_video_board_candidate"
MAGIC = b"TELLME_M184_V1\n"
PACKAGE_SHA = "1596536bfe6865cb7eab5c038d8b4da8b666afc7cbd629ddc4559781727151d6"
M182_SHA = "da6c69cb91a3956def857616f16d45358dd909b90967e110ad7e3a451b7e4f50"


def sha256(path: Path) -> str:
    value = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(32 << 20), b""):
            value.update(block)
    return value.hexdigest()


def receive_exact(stream: socket.socket, count: int) -> bytes:
    value = bytearray(count)
    view = memoryview(value)
    offset = 0
    while offset < count:
        observed = stream.recv_into(view[offset:], count - offset)
        if observed == 0:
            raise RuntimeError("M184 receiver closed before acknowledgement")
        offset += observed
    return bytes(value)


def build_manifest() -> tuple[dict[str, Path], dict]:
    package_path = CANDIDATE / "PACKAGE_MANIFEST.json"
    if sha256(package_path) != PACKAGE_SHA:
        raise RuntimeError("M184 local package manifest mismatch")
    package = json.loads(package_path.read_text(encoding="utf-8"))
    declared = {item["path"]: item for item in package["files"]}
    expected = set(declared) | {"PACKAGE_MANIFEST.json", "PACKAGE_READY.json"}
    actual = {p.relative_to(CANDIDATE).as_posix() for p in CANDIDATE.rglob("*") if p.is_file()}
    if actual != expected:
        raise RuntimeError("M184 local candidate closure mismatch")
    sources = {relative: CANDIDATE / relative for relative in sorted(actual)}
    entries = []
    for relative, path in sources.items():
        if "__pycache__" in path.parts or path.suffix == ".pyc" or path.name.endswith(".partial"):
            raise RuntimeError(f"M184 forbidden source path: {relative}")
        entries.append({"path": relative, "bytes": path.stat().st_size, "sha256": sha256(path)})
    manifest = {
        "gate": "M184-M181-video-direct-Ethernet-payload",
        "status": "PASS",
        "candidate_build_id": "0x4D395832",
        "package_manifest_sha256": PACKAGE_SHA,
        "m182_result_sha256": M182_SHA,
        "files": entries,
        "file_count": len(entries),
        "total_bytes": sum(item["bytes"] for item in entries),
    }
    return sources, manifest


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--host", default="192.168.0.2")
    parser.add_argument("--port", type=int, default=8767)
    args = parser.parse_args()
    if args.host != "192.168.0.2" or args.port != 8767:
        raise RuntimeError("M184 fixed endpoint identity mismatch")
    sources, manifest = build_manifest()
    payload = (json.dumps(manifest, separators=(",", ":")) + "\n").encode("utf-8")
    entries = manifest["files"]
    with socket.create_connection((args.host, args.port), timeout=30) as connection:
        connection.settimeout(1800)
        connection.sendall(MAGIC + struct.pack("!I", len(payload)) + payload)
        for ordinal, entry in enumerate(entries, 1):
            relative = entry["path"]
            encoded = relative.encode("utf-8")
            connection.sendall(struct.pack("!H", len(encoded)) + encoded + struct.pack("!Q", int(entry["bytes"])))
            with sources[relative].open("rb") as stream:
                for block in iter(lambda: stream.read(4 << 20), b""):
                    connection.sendall(block)
            print(f"M184_SEND_MEMBER_PASS ordinal={ordinal}/{len(entries)} path={relative} bytes={entry['bytes']}", flush=True)
        connection.sendall(b"\x00\x00")
        ack_size = struct.unpack("!I", receive_exact(connection, 4))[0]
        if ack_size <= 0 or ack_size > (1 << 20):
            raise RuntimeError("M184 unsafe acknowledgement size")
        ack = json.loads(receive_exact(connection, ack_size))
    if ack.get("status") != "PASS" or ack.get("package_manifest_sha256") != PACKAGE_SHA:
        raise RuntimeError(f"M184 board acknowledgement failed: {ack}")
    print(json.dumps(ack, indent=2))
    print("M184_M181_VIDEO_PC_PUSH_PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
