#!/usr/bin/env python3
"""Push the exact M189 ARM64 runtime bundle to the KV260."""

from __future__ import annotations

import argparse
import hashlib
import json
import socket
import struct
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
BUNDLE = ROOT / "deployment/mage_vl4b/m189_arm64_mage_runtime_bundle"
MAGIC = b"TELLME_M190_V1\n"
BUNDLE_SHA = "88c3fefaae94a475751bef3348e0048f30fc90bb1f27caa20e79f2e0f77361ba"


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
            raise RuntimeError("M190 receiver closed before acknowledgement")
        offset += observed
    return bytes(value)


def build_manifest() -> tuple[dict[str, Path], dict]:
    manifest_path = BUNDLE / "BUNDLE_MANIFEST.json"
    if sha256(manifest_path) != BUNDLE_SHA:
        raise RuntimeError("M190 local bundle manifest mismatch")
    bundle = json.loads(manifest_path.read_text(encoding="utf-8"))
    declared = {item["path"]: item for item in bundle["files"]}
    expected = set(declared) | {"BUNDLE_MANIFEST.json", "BUNDLE_READY.json"}
    actual = {p.name for p in BUNDLE.iterdir() if p.is_file()}
    if actual != expected or any("/" in name or "\\" in name for name in actual):
        raise RuntimeError("M190 local bundle closure mismatch")
    sources = {name: BUNDLE / name for name in sorted(actual)}
    entries = [
        {"path": name, "bytes": path.stat().st_size, "sha256": sha256(path)}
        for name, path in sources.items()
    ]
    return sources, {
        "gate": "M190-M189-ARM64-runtime-direct-Ethernet-payload",
        "status": "PASS",
        "bundle_manifest_sha256": BUNDLE_SHA,
        "files": entries,
        "file_count": len(entries),
        "total_bytes": sum(item["bytes"] for item in entries),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--host", default="192.168.0.2")
    parser.add_argument("--port", type=int, default=8768)
    args = parser.parse_args()
    if args.host != "192.168.0.2" or args.port != 8768:
        raise RuntimeError("M190 fixed endpoint identity mismatch")
    sources, manifest = build_manifest()
    payload = (json.dumps(manifest, separators=(",", ":")) + "\n").encode()
    with socket.create_connection((args.host, args.port), timeout=30) as connection:
        connection.settimeout(3600)
        connection.sendall(MAGIC + struct.pack("!I", len(payload)) + payload)
        for ordinal, entry in enumerate(manifest["files"], 1):
            relative = entry["path"]
            encoded = relative.encode()
            connection.sendall(struct.pack("!H", len(encoded)) + encoded + struct.pack("!Q", entry["bytes"]))
            with sources[relative].open("rb") as stream:
                for block in iter(lambda: stream.read(4 << 20), b""):
                    connection.sendall(block)
            print(f"M190_SEND_MEMBER_PASS ordinal={ordinal}/{manifest['file_count']} path={relative}", flush=True)
        connection.sendall(b"\x00\x00")
        size = struct.unpack("!I", receive_exact(connection, 4))[0]
        acknowledgement = json.loads(receive_exact(connection, size))
    if acknowledgement.get("status") != "PASS" or acknowledgement.get("bundle_manifest_sha256") != BUNDLE_SHA:
        raise RuntimeError(f"M190 board acknowledgement failed: {acknowledgement}")
    print(json.dumps(acknowledgement, indent=2))
    print("M190_ARM64_RUNTIME_PC_PUSH_PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
