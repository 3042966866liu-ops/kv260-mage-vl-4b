#!/usr/bin/env python3
"""Retire only the exact, recoverable v4 isolated install before clean v5."""

import hashlib
import json
import os
from pathlib import Path
import shutil


TARGET = Path("/home/ubuntu/tellme_release_install_20260926")
STABLE = Path("/home/ubuntu/tellme_m120_m89x2_20260901")
ARCHIVE_SHA = "f6a7991a2c36ae8eab0c1ca5ac3a80829f5b09a7efbfc151e581ce5e5a9847df"
MANIFEST_SHA = "be4d04e70df51cc37a5810924f2c1e2645f8dde2361dd4c547ac27e52c21abf3"


def main():
    if os.geteuid() != 0 or TARGET.resolve() != TARGET or not TARGET.is_dir() or TARGET.is_symlink():
        raise RuntimeError("exact isolated v4 target required")
    if not STABLE.is_dir() or STABLE == TARGET or STABLE in TARGET.parents:
        raise RuntimeError("stable rollback directory check failed")
    record = json.loads((TARGET / "INSTALL_BOARD_RESULT.json").read_text(encoding="utf-8"))
    if (record.get("status") != "PASS_INSTALLED_FILES_NOT_YET_EXECUTED"
            or record.get("archive_sha256") != ARCHIVE_SHA
            or record.get("manifest_sha256") != MANIFEST_SHA
            or record.get("directory") != str(TARGET)):
        raise RuntimeError("v4 identity check failed")
    if hashlib.sha256((TARGET / "INSTALL_PACKAGE_MANIFEST.json").read_bytes()).hexdigest() != MANIFEST_SHA:
        raise RuntimeError("v4 manifest bytes changed")
    for proc in Path("/proc").iterdir():
        if proc.name.isdigit():
            try:
                command = (proc / "cmdline").read_bytes()
            except (OSError, PermissionError):
                continue
            if str(TARGET).encode() in command:
                raise RuntimeError(f"v4 still referenced by process {proc.name}")
    shutil.rmtree(TARGET)
    print(json.dumps({"status": "REMOVED_ISOLATED_V4_AFTER_ARCHIVE_AND_LOG_BACKUP",
                      "path": str(TARGET), "archive_sha256": ARCHIVE_SHA}), flush=True)
    print("M327_V4_INSTALL_REMOVED_PASS", flush=True)


if __name__ == "__main__":
    main()
