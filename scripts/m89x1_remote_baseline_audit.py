#!/usr/bin/env python3
"""Read-only identity and closure audit for retained M89-X1 board packages."""

from __future__ import annotations

import argparse
import base64
import hashlib
import json
from pathlib import Path


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(8 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def audit(root: Path) -> dict:
    root = root.resolve()
    manifest_path = root / "PACKAGE_MANIFEST.json"
    result = {
        "root": str(root),
        "exists": root.is_dir(),
        "manifest_exists": manifest_path.is_file(),
    }
    if not manifest_path.is_file():
        return result
    raw = manifest_path.read_bytes()
    manifest = json.loads(raw.decode("utf-8"))
    expected = {"PACKAGE_MANIFEST.json"}
    bad = []
    for item in manifest.get("files", []):
        relative = item["path"]
        expected.add(relative)
        path = root / relative
        if not path.is_file():
            bad.append({"path": relative, "reason": "missing"})
            continue
        if path.stat().st_size != int(item["bytes"]):
            bad.append({"path": relative, "reason": "size"})
            continue
        observed = sha256(path)
        if observed != item["sha256"]:
            bad.append({"path": relative, "reason": "sha256", "observed": observed})
    actual = {
        path.relative_to(root).as_posix()
        for path in root.rglob("*")
        if path.is_file()
    }
    result.update(
        {
            "manifest_sha256": hashlib.sha256(raw).hexdigest(),
            "declared_file_count": len(manifest.get("files", [])),
            "bad": bad,
            "missing": sorted(expected - actual),
            "extra": sorted(actual - expected),
            "closure_pass": not bad and actual == expected,
            "manifest_base64": base64.b64encode(raw).decode("ascii"),
        }
    )
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--self-sha256", required=True)
    parser.add_argument("--candidate", action="append", type=Path, required=True)
    args = parser.parse_args()
    if sha256(Path(__file__)) != args.self_sha256:
        raise RuntimeError("audit runner self hash mismatch")
    roots = [path.resolve() for path in args.candidate]
    home = Path("/home/ubuntu").resolve()
    if any(home not in (path, *path.parents) for path in roots):
        raise RuntimeError("candidate path outside /home/ubuntu")
    payload = {"gate": "M89-X1-remote-baseline-audit", "results": [audit(path) for path in roots]}
    print("M89X1_REMOTE_BASELINE_AUDIT_BEGIN")
    print(json.dumps(payload, sort_keys=True, separators=(",", ":")))
    print("M89X1_REMOTE_BASELINE_AUDIT_END")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
