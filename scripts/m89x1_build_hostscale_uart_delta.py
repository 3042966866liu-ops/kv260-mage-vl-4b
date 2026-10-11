#!/usr/bin/env python3
"""Create a deterministic UART delta from M89-X1 baseline to HS64 v2."""

from __future__ import annotations

import argparse
import gzip
import hashlib
import io
import json
import tarfile
from pathlib import Path


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--baseline", type=Path, required=True)
    parser.add_argument("--candidate", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    baseline, candidate = args.baseline.resolve(), args.candidate.resolve()
    old = json.loads((baseline / "PACKAGE_MANIFEST.json").read_text(encoding="utf-8"))
    new = json.loads((candidate / "PACKAGE_MANIFEST.json").read_text(encoding="utf-8"))
    old_hashes = {item["path"]: item["sha256"] for item in old["files"]}
    changed = [item["path"] for item in new["files"]
               if old_hashes.get(item["path"]) != item["sha256"]]
    changed.append("PACKAGE_MANIFEST.json")
    raw = io.BytesIO()
    with tarfile.open(fileobj=raw, mode="w", format=tarfile.PAX_FORMAT) as archive:
        for relative in sorted(changed):
            path = candidate / relative
            info = archive.gettarinfo(str(path), arcname=relative)
            info.uid = info.gid = 0
            info.uname = info.gname = ""
            info.mtime = 0
            with path.open("rb") as handle:
                archive.addfile(info, handle)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("wb") as destination:
        with gzip.GzipFile(filename="", mode="wb", fileobj=destination, mtime=0) as compressed:
            compressed.write(raw.getvalue())
    result = {
        "gate": "M89-X1-HS64-UART-delta",
        "status": "PASS",
        "changed_files": sorted(changed),
        "changed_file_count": len(changed),
        "delta_bytes": args.output.stat().st_size,
        "delta_sha256": sha256(args.output),
        "baseline_manifest_sha256": sha256(baseline / "PACKAGE_MANIFEST.json"),
        "candidate_manifest_sha256": sha256(candidate / "PACKAGE_MANIFEST.json"),
    }
    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
