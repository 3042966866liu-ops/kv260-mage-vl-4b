#!/usr/bin/env python3
"""Verify the clean M246 package and exact M243/M244 predecessors."""

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
parser.add_argument("--m243-result", type=Path, required=True)
parser.add_argument("--expected-m243-result-sha256", required=True)
args = parser.parse_args()
root = args.root.resolve()
manifest_path = root / "PACKAGE_MANIFEST.json"
if sha(manifest_path) != args.expected_manifest_sha256:
    raise RuntimeError("M246 package manifest hash mismatch")
manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
if manifest.get("status") != "PASS" or manifest.get("build_id") != "0x4D395832":
    raise RuntimeError("M246 package identity mismatch")
expected = {item["path"]: item for item in manifest["files"]}
observed = {
    path.relative_to(root).as_posix(): path
    for path in root.rglob("*")
    if path.is_file() and path.name != "PACKAGE_MANIFEST.json"
}
if set(expected) != set(observed):
    raise RuntimeError(
        f"M246 package closure mismatch missing={sorted(set(expected)-set(observed))} "
        f"extra={sorted(set(observed)-set(expected))}"
    )
for name, item in expected.items():
    path = observed[name]
    if path.stat().st_size != int(item["bytes"]) or sha(path) != item["sha256"]:
        raise RuntimeError(f"M246 package member mismatch: {name}")
if any("__pycache__" in path.parts or path.suffix == ".pyc" for path in observed.values()):
    raise RuntimeError("M246 forbidden Python cache")

if sha(args.m243_result) != args.expected_m243_result_sha256:
    raise RuntimeError("M246 exact M243 board result hash mismatch")
m243 = json.loads(args.m243_result.read_text(encoding="utf-8"))
if not (
    m243.get("status") == "PASS"
    and m243.get("final", {}).get("web_runtime_class") == "M243VideoRuntime"
    and m243.get("final", {}).get("web_board_runtime_class") == "M238PrefillRuntime"
    and m243.get("final", {}).get("web_language_model_class") == "M241VideoLanguageModel"
    and m243.get("frames_submitted") == 0
):
    raise RuntimeError("M246 M243 predecessor is not accepted")

m244_path = root / "M244_PREDECESSOR_RESULT.json"
if sha(m244_path) != manifest["m244_formal_result_sha256"]:
    raise RuntimeError("M246 packaged M244 predecessor hash mismatch")
m244 = json.loads(m244_path.read_text(encoding="utf-8"))
if not (
    m244.get("functional_status") == "FAIL"
    and m244.get("window_error", [{}])[0].get("error")
    == "RuntimeError: M152 generated no non-EOS token"
    and len([e for e in m244.get("events", []) if e.get("event") == "vision_layer_pass"]) == 24
    and m244.get("final", {}).get("runtime_load_count") == 1
):
    raise RuntimeError("M246 M244 failure identity mismatch")
print("M246_PACKAGE_VERIFY_PASS")

