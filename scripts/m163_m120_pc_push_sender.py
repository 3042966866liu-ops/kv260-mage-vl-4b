#!/usr/bin/env python3
"""Push the exact rehashed M120 payload to the KV260 over outbound TCP."""

from __future__ import annotations

import argparse
import json
import socket
import struct

from m162_m120_readonly_http_server import build_files


MAGIC = b"TELLME_M163_V1\n"


def receive_exact(stream: socket.socket, count: int) -> bytes:
    value = bytearray(count)
    view = memoryview(value)
    offset = 0
    while offset < count:
        observed = stream.recv_into(view[offset:], count - offset)
        if observed == 0:
            raise RuntimeError("M163 receiver closed before acknowledgement")
        offset += observed
    return bytes(value)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--host", default="192.168.0.2")
    parser.add_argument("--port", type=int, default=8766)
    args = parser.parse_args()
    if args.host != "192.168.0.2" or args.port != 8766:
        raise RuntimeError("M163 fixed endpoint identity mismatch")
    sources, manifest = build_files()
    manifest_bytes = (json.dumps(manifest, indent=2) + "\n").encode("utf-8")
    entries = manifest["files"]
    with socket.create_connection((args.host, args.port), timeout=30) as connection:
        connection.settimeout(900)
        connection.sendall(MAGIC + struct.pack("!I", len(manifest_bytes)) + manifest_bytes)
        for ordinal, entry in enumerate(entries, 1):
            relative = entry["path"]
            encoded = relative.encode("utf-8")
            connection.sendall(struct.pack("!H", len(encoded)) + encoded + struct.pack("!Q", int(entry["bytes"])))
            with sources[relative].open("rb") as stream:
                for block in iter(lambda: stream.read(4 << 20), b""):
                    connection.sendall(block)
            print(f"M163_SEND_MEMBER_PASS ordinal={ordinal}/{len(entries)} path={relative} bytes={entry['bytes']}", flush=True)
        connection.sendall(b"\x00\x00")
        ack_size = struct.unpack("!I", receive_exact(connection, 4))[0]
        if ack_size <= 0 or ack_size > (1 << 20):
            raise RuntimeError(f"M163 unsafe acknowledgement size: {ack_size}")
        ack = json.loads(receive_exact(connection, ack_size))
    if ack.get("status") != "PASS" or int(ack.get("payload_bytes", -1)) != 2_035_472_384:
        raise RuntimeError(f"M163 board acknowledgement failed: {ack}")
    print(json.dumps(ack, indent=2))
    print("M163_M120_PC_PUSH_PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
