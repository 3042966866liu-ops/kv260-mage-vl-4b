#!/usr/bin/env python3
"""Fail-closed static-package swap for the active M254 Web service."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import urllib.request


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(4 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def verify_package(root: Path, expected_manifest_sha256: str) -> dict:
    manifest_path = root / "PACKAGE_MANIFEST.json"
    if sha256(manifest_path) != expected_manifest_sha256:
        raise RuntimeError(f"manifest hash mismatch at {root}")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if manifest.get("gate") != "M254-dual-path-Web-board-candidate" or manifest.get("status") != "PASS":
        raise RuntimeError(f"package identity mismatch at {root}")
    records = manifest.get("files")
    if not isinstance(records, list) or len(records) != manifest.get("file_count"):
        raise RuntimeError(f"manifest record count mismatch at {root}")
    expected = sorted(str(item["path"]) for item in records)
    observed = sorted(
        path.relative_to(root).as_posix()
        for path in root.rglob("*")
        if path.is_file() and path.name != "PACKAGE_MANIFEST.json"
    )
    if observed != expected:
        raise RuntimeError(f"package closure mismatch at {root}")
    for item in records:
        path = root / item["path"]
        if path.stat().st_size != int(item["bytes"]) or sha256(path) != item["sha256"]:
            raise RuntimeError(f"payload mismatch: {path}")
    if any(path.suffix == ".pyc" or "__pycache__" in path.parts for path in root.rglob("*")):
        raise RuntimeError(f"forbidden cache path at {root}")
    return manifest


def request_status() -> dict:
    request = urllib.request.Request("http://127.0.0.1:8001/api/4b/video/live/status", headers={"Cache-Control": "no-store"})
    with urllib.request.urlopen(request, timeout=10) as response:
        return json.loads(response.read().decode("utf-8"))


def request_app() -> bytes:
    request = urllib.request.Request("http://127.0.0.1:8001/app.js?m255=1", headers={"Cache-Control": "no-store"})
    with urllib.request.urlopen(request, timeout=10) as response:
        return response.read()


def require_active_m254(status: dict) -> None:
    fast = status.get("fast_path") or {}
    if not (
        status.get("status") == "running"
        and status.get("mode") == "M254-dual-path-latest-only"
        and fast.get("runtime_load_count") == 1
        and status.get("semantic_review") is not None
    ):
        raise RuntimeError(f"active M254 identity mismatch: {status}")


def write_result(path: Path, value: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    partial = path.with_name(path.name + ".partial")
    partial.write_text(json.dumps(value, indent=2) + "\n", encoding="utf-8")
    os.replace(partial, path)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--current", type=Path, required=True)
    parser.add_argument("--staging", type=Path, required=True)
    parser.add_argument("--rollback", type=Path, required=True)
    parser.add_argument("--old-manifest-sha256", required=True)
    parser.add_argument("--new-manifest-sha256", required=True)
    parser.add_argument("--app-js-sha256", required=True)
    parser.add_argument("--result", type=Path, required=True)
    args = parser.parse_args()
    swapped = False
    restored = False
    before_status = None
    before_app_sha256 = None
    try:
        if args.rollback.exists():
            raise RuntimeError(f"rollback path already exists: {args.rollback}")
        old_manifest = verify_package(args.current, args.old_manifest_sha256)
        new_manifest = verify_package(args.staging, args.new_manifest_sha256)
        if new_manifest.get("release") != "R4-M255-active-session-attach":
            raise RuntimeError("M255 R4 release identity missing")
        if sha256(args.staging / "static/app.js") != args.app_js_sha256:
            raise RuntimeError("M255 staged app.js hash mismatch")
        before_status = request_status()
        require_active_m254(before_status)
        before_app_sha256 = sha256_bytes(request_app())
        if before_app_sha256 == args.app_js_sha256:
            raise RuntimeError("M255 hotfix already appears active")

        os.replace(args.current, args.rollback)
        try:
            os.replace(args.staging, args.current)
            swapped = True
        except Exception:
            os.replace(args.rollback, args.current)
            restored = True
            raise

        verify_package(args.current, args.new_manifest_sha256)
        served_app_sha256 = sha256_bytes(request_app())
        if served_app_sha256 != args.app_js_sha256:
            raise RuntimeError(f"served app.js mismatch: {served_app_sha256}")
        after_status = request_status()
        require_active_m254(after_status)
        before_load = int((before_status.get("fast_path") or {}).get("runtime_load_count", -1))
        after_load = int((after_status.get("fast_path") or {}).get("runtime_load_count", -2))
        if after_load != before_load:
            raise RuntimeError(f"runtime load count changed {before_load}->{after_load}")
        result = {
            "date": "2026-09-02",
            "gate": "M255-KV260-active-M254-session-Web-fix",
            "status": "PASS",
            "classification": "Real KV260 static Web hotfix: existing M254 runtime remains active and load-count stable; app.js now attaches after the exact active-session conflict. No frame inference or accuracy claim is made by this gate.",
            "old_manifest_sha256": args.old_manifest_sha256,
            "new_manifest_sha256": args.new_manifest_sha256,
            "old_release": old_manifest.get("release", "R3"),
            "new_release": new_manifest["release"],
            "old_app_js_sha256": before_app_sha256,
            "served_app_js_sha256": served_app_sha256,
            "active_mode": after_status["mode"],
            "fast_runtime_load_count_before": before_load,
            "fast_runtime_load_count_after": after_load,
            "candidate_service_restarted": False,
            "model_or_fpga_reloaded": False,
            "rollback_directory": str(args.rollback),
            "boot_dtb_cma_partitions_changed": False,
            "next_gate": "Reload the browser page, select the labelled local MP4, start monitoring, and require accepted frames plus the first structured safety_result.",
        }
        write_result(args.result, result)
        print("__M255_BOARD_RESULT_BEGIN__")
        print(json.dumps(result, separators=(",", ":")))
        print("__M255_BOARD_RESULT_END__")
        print("M255_ACTIVE_SESSION_WEB_FIX_BOARD_PASS")
        return 0
    except Exception as exc:
        if swapped:
            rejected = args.current.with_name(args.current.name + ".m255-rejected")
            if args.current.exists() and not rejected.exists():
                os.replace(args.current, rejected)
            if args.rollback.exists():
                os.replace(args.rollback, args.current)
                restored = True
        result = {
            "date": "2026-09-02",
            "gate": "M255-KV260-active-M254-session-Web-fix",
            "status": "FAIL",
            "error": f"{type(exc).__name__}: {exc}",
            "swap_started": swapped,
            "r3_restored": restored,
            "boot_dtb_cma_partitions_changed": False,
        }
        write_result(args.result, result)
        print("__M255_BOARD_RESULT_BEGIN__")
        print(json.dumps(result, separators=(",", ":")))
        print("__M255_BOARD_RESULT_END__")
        print("M255_ACTIVE_SESSION_WEB_FIX_BOARD_FAIL")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
