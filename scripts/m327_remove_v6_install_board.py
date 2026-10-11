#!/usr/bin/env python3
"""Retire only exact, recoverable v6 isolated install before clean v7."""

import hashlib
import json
import os
from pathlib import Path
import shutil


TARGET = Path("/home/ubuntu/tellme_release_install_20260926")
STABLE = Path("/home/ubuntu/tellme_m120_m89x2_20260901")
ARCHIVE_SHA = "40f28774a1f7c7908671ce2fbb7d32a207ab71cff0510387d8c888be127d76c6"
MANIFEST_SHA = "5244ea31b2ba431727ba5633cf458f41d1cfae2e0d811d0e826d6db8a36342a9"


def main():
    if os.geteuid() != 0 or TARGET.resolve() != TARGET or not TARGET.is_dir() or TARGET.is_symlink():
        raise RuntimeError("exact isolated v6 target required")
    if not STABLE.is_dir() or STABLE == TARGET or STABLE in TARGET.parents:
        raise RuntimeError("stable rollback directory check failed")
    record = json.loads((TARGET / "INSTALL_BOARD_RESULT.json").read_text(encoding="utf-8"))
    if (record.get("status") != "PASS_INSTALLED_FILES_NOT_YET_EXECUTED"
            or record.get("archive_sha256") != ARCHIVE_SHA
            or record.get("manifest_sha256") != MANIFEST_SHA
            or record.get("directory") != str(TARGET)):
        raise RuntimeError("v6 identity check failed")
    if hashlib.sha256((TARGET / "INSTALL_PACKAGE_MANIFEST.json").read_bytes()).hexdigest() != MANIFEST_SHA:
        raise RuntimeError("v6 manifest bytes changed")
    for proc in Path("/proc").iterdir():
        if proc.name.isdigit():
            try:
                command = (proc / "cmdline").read_bytes()
            except (OSError, PermissionError):
                continue
            if str(TARGET).encode() in command:
                raise RuntimeError(f"v6 still referenced by process {proc.name}")
    shutil.rmtree(TARGET)
    print(json.dumps({"status": "REMOVED_ISOLATED_V6_AFTER_ARCHIVE_AND_LOG_BACKUP",
                      "path": str(TARGET), "archive_sha256": ARCHIVE_SHA}), flush=True)
    print("M327_V6_INSTALL_REMOVED_PASS", flush=True)


if __name__ == "__main__":
    main()
