#!/usr/bin/env python3
"""Build a clean, whitelisted, hash-checked M335 UART transfer package."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import tarfile
import tempfile


FILES = (
    "m335_review_bridge.py", "m335_video_server.py", "m335_board_gate.py",
    "run_m335_board.sh", "static/index.html", "static/app.js", "static/style.css",
)


def digest(path: Path) -> str:
    value = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            value.update(block)
    return value.hexdigest()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--candidate", type=Path, required=True)
    parser.add_argument("--archive", type=Path, required=True)
    args = parser.parse_args()
    source = args.candidate.resolve()
    archive = args.archive.resolve()
    archive.parent.mkdir(parents=True, exist_ok=True)
    rows = []
    for name in FILES:
        path = source / name
        if not path.is_file() or path.is_symlink():
            raise RuntimeError(f"missing or symlinked package member: {name}")
        rows.append({"path": name, "bytes": path.stat().st_size, "sha256": digest(path)})
    with tempfile.TemporaryDirectory(prefix="m335-clean-stage-") as temp:
        stage = Path(temp)
        for item in rows:
            dest = stage / item["path"]
            dest.parent.mkdir(parents=True, exist_ok=True)
            dest.write_bytes((source / item["path"]).read_bytes())
        sums = "".join(f"{item['sha256']}  {item['path']}\n" for item in rows)
        (stage / "PACKAGE_SHA256SUMS.txt").write_bytes(sums.encode("ascii"))
        with tarfile.open(archive, "w:gz") as tar:
            for name in (*FILES, "PACKAGE_SHA256SUMS.txt"):
                tar.add(stage / name, arcname=name, recursive=False)
    print(json.dumps({"archive": str(archive), "archive_sha256": digest(archive),
                      "file_count": len(rows), "payload_bytes": sum(item["bytes"] for item in rows),
                      "files": rows}, indent=2))


if __name__ == "__main__":
    main()
