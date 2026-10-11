#!/usr/bin/env python3
"""Audit the exact M120 T32 language/head payload before any USB copy."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path


EXPECTED_RESULT_SHA = None
EXPECTED_LANGUAGE_MANIFEST = "12ea4b8cc58639d0aab6da4ef3a3f12bbbb1254f88865f76512a5f0d00d4ae5d"
EXPECTED_HEAD_MANIFEST = "a1a555700e3daec8049627564c73e5783affe3827ab5437665249786d5c079ef"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(32 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def atomic_json(path: Path, value: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + f".tmp-{os.getpid()}")
    temporary.write_text(json.dumps(value, indent=2) + "\n", encoding="utf-8")
    os.replace(temporary, path)


def verify_layout(root: Path, expected_manifest: str, expected_modules: int) -> dict:
    manifest_path = root / "SIXPORT_LAYOUT_MANIFEST.json"
    observed_manifest = sha256(manifest_path)
    if observed_manifest != expected_manifest:
        raise RuntimeError(f"layout manifest mismatch: {root}")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if len(manifest.get("modules", [])) != expected_modules:
        raise RuntimeError(f"module closure mismatch: {root}")
    declared = manifest.get("files")
    if not isinstance(declared, list) or len(declared) != 4:
        raise RuntimeError(f"four-shard declaration absent: {root}")
    expected_paths = {"SIXPORT_LAYOUT_MANIFEST.json"}
    verified = []
    for index, item in enumerate(declared):
        if item.get("path") != f"weights{index}.bin":
            raise RuntimeError(f"shard order mismatch: {root}")
        path = root / item["path"]
        if path.stat().st_size != int(item["bytes"]):
            raise RuntimeError(f"shard size mismatch: {path}")
        observed = sha256(path)
        if observed != item["sha256"]:
            raise RuntimeError(f"shard hash mismatch: {path}")
        expected_paths.add(item["path"])
        verified.append({"path": item["path"], "bytes": path.stat().st_size, "sha256": observed})
    actual_paths = {path.relative_to(root).as_posix() for path in root.rglob("*") if path.is_file()}
    if actual_paths != expected_paths:
        raise RuntimeError(f"layout path closure mismatch: {root}")
    return {
        "root": str(root.resolve()),
        "manifest_sha256": observed_manifest,
        "module_count": expected_modules,
        "files": verified,
        "mapped_bytes": sum(item["bytes"] for item in verified),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--layout-root", type=Path, required=True)
    parser.add_argument("--m125-result", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    result: dict[str, object] = {
        "date": "2026-09-01",
        "gate": "M141-M120-fulltext-USB-source-audit",
        "status": "FAIL",
        "classification": "Read-only WSL payload identity audit; not USB copy, board, layer, E2E, performance, video or Web evidence.",
    }
    try:
        m125 = json.loads(args.m125_result.read_text(encoding="utf-8"))
        if m125.get("status") != "PASS_EXACT_M120_LANGUAGE_AND_HEAD_FOURPORT_LAYOUTS":
            raise RuntimeError("M125 source result is not PASS")
        if m125["language"]["manifest_sha256"] != EXPECTED_LANGUAGE_MANIFEST:
            raise RuntimeError("M125 language identity drift")
        if m125["lm_head"]["manifest_sha256"] != EXPECTED_HEAD_MANIFEST:
            raise RuntimeError("M125 LM-head identity drift")
        language = verify_layout(args.layout_root / "language_fourport", EXPECTED_LANGUAGE_MANIFEST, 252)
        head = verify_layout(args.layout_root / "lmhead_fourport", EXPECTED_HEAD_MANIFEST, 1)
        if language["mapped_bytes"] != 1_828_839_424:
            raise RuntimeError("language mapped byte mismatch")
        if head["mapped_bytes"] != 206_632_960:
            raise RuntimeError("LM-head mapped byte mismatch")
        payload_bytes = language["mapped_bytes"] + head["mapped_bytes"]
        result.update(
            {
                "status": "PASS",
                "language": language,
                "lm_head": head,
                "payload_bytes": payload_bytes,
                "payload_gib": payload_bytes / (1 << 30),
                "usb_required_free_bytes": payload_bytes + (64 << 20),
                "usb_copy_started": False,
                "board_state_changed": False,
                "next_gate": "After M140 single-chain PASS, copy this exact eight-shard payload plus manifests to a clean USB staging directory and verify every hash again."
            }
        )
    except Exception as exc:
        result["error"] = f"{type(exc).__name__}: {exc}"
        result["next_gate"] = "Repair only this source audit; do not copy the payload or run a broader board gate."
    atomic_json(args.output, result)
    print(json.dumps(result, indent=2), flush=True)
    print("M141_M120_USB_SOURCE_AUDIT_PASS" if result["status"] == "PASS" else "M141_M120_USB_SOURCE_AUDIT_FAIL")
    return 0 if result["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
