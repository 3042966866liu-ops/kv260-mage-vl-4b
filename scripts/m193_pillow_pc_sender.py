#!/usr/bin/env python3
"""Send the exact ARM64 Pillow repair wheel to M193."""

import hashlib, json, socket, struct
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
WHEEL = ROOT / "tmp/m193_pillow_arm64/pillow-12.1.0-cp310-cp310-manylinux2014_aarch64.manylinux_2_17_aarch64.whl"
MAGIC = b"TELLME_M193_V1\n"


def sha256(path):
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(4 << 20), b""):
            h.update(block)
    return h.hexdigest()


def exact(sock, size):
    data = bytearray()
    while len(data) < size:
        block = sock.recv(size - len(data))
        if not block:
            raise RuntimeError("M193 early acknowledgement EOF")
        data.extend(block)
    return bytes(data)


def main():
    identity = {"name": WHEEL.name, "bytes": WHEEL.stat().st_size, "sha256": sha256(WHEEL)}
    payload = json.dumps(identity, separators=(",", ":")).encode()
    with socket.create_connection(("192.168.0.2", 8769), timeout=30) as sock:
        sock.settimeout(1800)
        sock.sendall(MAGIC + struct.pack("!I", len(payload)) + payload)
        with WHEEL.open("rb") as f:
            for block in iter(lambda: f.read(4 << 20), b""):
                sock.sendall(block)
        size = struct.unpack("!I", exact(sock, 4))[0]
        result = json.loads(exact(sock, size))
    print(json.dumps(result, indent=2))
    if result.get("status") != "PASS":
        raise RuntimeError(f"M193 repair acknowledgement failed: {result}")
    print("M193_PILLOW_PC_PUSH_PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
