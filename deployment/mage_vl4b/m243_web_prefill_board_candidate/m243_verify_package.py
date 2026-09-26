#!/usr/bin/env python3
"""Verify M243 closure and exact M242 predecessor evidence."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


parser = argparse.ArgumentParser()
parser.add_argument("--root", type=Path, required=True)
parser.add_argument("--expected-manifest-sha256", required=True)
parser.add_argument("--m242-result", type=Path, required=True)
parser.add_argument("--expected-m242-result-sha256", required=True)
args = parser.parse_args()
root = args.root.resolve()
manifest_path = root / "PACKAGE_MANIFEST.json"
if sha(manifest_path) != args.expected_manifest_sha256:
    raise RuntimeError("M243 package manifest hash mismatch")
manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
expected = {item["path"] for item in manifest["files"]} | {"PACKAGE_MANIFEST.json"}
actual = {path.relative_to(root).as_posix() for path in root.rglob("*") if path.is_file()}
if manifest.get("gate") != "M243-web-prefill-runtime-delta" or actual != expected:
    raise RuntimeError("M243 package identity/closure mismatch")
for item in manifest["files"]:
    path = root / item["path"]
    if path.stat().st_size != int(item["bytes"]) or sha(path) != item["sha256"]:
        raise RuntimeError(f"M243 member mismatch: {item['path']}")
if sha(args.m242_result) != args.expected_m242_result_sha256:
    raise RuntimeError("M242 formal result hash mismatch")
m242 = json.loads(args.m242_result.read_text(encoding="utf-8"))
acceptance = m242.get("acceptance", m242)
if not (
    acceptance.get("gate") == "M242-real-KV260-M241-fixed-text-acceptance"
    and acceptance.get("status") == "PASS"
    and acceptance.get("fixed_text", {}).get("generated_token_id") == 17
    and acceptance.get("fixed_text", {}).get("fpga_execution_proved") is True
    and acceptance.get("fixed_text", {}).get("cpu_linear_fallback") is False
):
    raise RuntimeError("M242 predecessor is not accepted")
print("M243_PACKAGE_AND_M242_PREDECESSOR_VERIFY_PASS")
