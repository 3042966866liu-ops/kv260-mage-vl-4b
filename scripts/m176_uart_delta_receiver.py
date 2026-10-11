#!/usr/bin/env python3
"""Receive one manifest-declared M176 delta member over line-delimited base64."""

import base64
import hashlib
import os
import sys
import termios
from pathlib import Path


ROOT = Path("/home/ubuntu/tellme_m120_m89x2_20260901/m176_delta_01").resolve()
EOF = "__M176_UART_FILE_EOF__"


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


path = Path(sys.argv[1]).resolve()
size = int(sys.argv[2])
expected = sys.argv[3]
manifest_expected = sys.argv[4]
self_expected = sys.argv[5]
if digest(Path(__file__)) != self_expected:
    raise RuntimeError("M176 receiver self hash mismatch")
manifest_path = ROOT / "DELTA_MANIFEST.json"
if digest(manifest_path) != manifest_expected:
    raise RuntimeError("M176 delta manifest hash mismatch")
import json
manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
allowed = {ROOT / item["path"]: (int(item["bytes"]), item["sha256"]) for item in manifest["files"]}
if path not in allowed or allowed[path] != (size, expected):
    raise RuntimeError("M176 member identity mismatch")
if path.exists():
    if path.stat().st_size == size and digest(path) == expected:
        print("M176_UART_FILE_ALREADY_VERIFIED", flush=True)
        print("M176_UART_FILE_RECEIVE_PASS", flush=True)
        raise SystemExit(0)
    raise RuntimeError("M176 existing member identity mismatch")
partial = Path(str(path) + ".partial")
if partial.exists():
    raise RuntimeError("M176 partial exists")
attributes = termios.tcgetattr(0)
quiet = attributes.copy()
quiet[3] &= ~termios.ECHO
termios.tcsetattr(0, termios.TCSANOW, quiet)
lines = []
print("M176_UART_FILE_RECEIVER_READY", flush=True)
try:
    while True:
        line = sys.stdin.readline()
        if not line:
            raise RuntimeError("M176 UART closed")
        line = line.strip()
        if line == EOF:
            break
        lines.append(line)
finally:
    termios.tcsetattr(0, termios.TCSANOW, attributes)
data = base64.b64decode("".join(lines), validate=True)
if len(data) != size or hashlib.sha256(data).hexdigest() != expected:
    raise RuntimeError("M176 streamed member identity mismatch")
path.parent.mkdir(parents=True, exist_ok=True)
try:
    partial.write_bytes(data)
    os.chmod(partial, 0o755)
    os.replace(partial, path)
finally:
    if partial.exists():
        partial.unlink()
print("M176_UART_FILE_VERIFIED", size, expected, flush=True)
print("M176_UART_FILE_RECEIVE_PASS", flush=True)
