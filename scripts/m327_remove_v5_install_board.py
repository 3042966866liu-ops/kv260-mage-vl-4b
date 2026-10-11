#!/usr/bin/env python3
"""Retire only the exact, archived v5 isolated install before clean v6."""

import hashlib
import json
import os
from pathlib import Path
import shutil


TARGET = Path("/home/ubuntu/tellme_release_install_20260926")
STABLE = Path("/home/ubuntu/tellme_m120_m89x2_20260901")
ARCHIVE_SHA = "81bdd8f713e0e270850b5db56bad97cbf03c28aa45619309f46c90edaa17c4dc"
MANIFEST_SHA = "fb801b39f19ec54b5437c557300512aba78ae62daa0c22189b1889defebac269"


def main():
    if os.geteuid() != 0 or TARGET.resolve() != TARGET or not TARGET.is_dir() or TARGET.is_symlink():
        raise RuntimeError("exact isolated v5 target required")
    if not STABLE.is_dir() or STABLE == TARGET or STABLE in TARGET.parents:
        raise RuntimeError("stable rollback directory check failed")
    record = json.loads((TARGET / "INSTALL_BOARD_RESULT.json").read_text(encoding="utf-8"))
    if (record.get("status") != "PASS_INSTALLED_FILES_NOT_YET_EXECUTED"
            or record.get("archive_sha256") != ARCHIVE_SHA
            or record.get("manifest_sha256") != MANIFEST_SHA
            or record.get("directory") != str(TARGET)):
        raise RuntimeError("v5 identity check failed")
    if hashlib.sha256((TARGET / "INSTALL_PACKAGE_MANIFEST.json").read_bytes()).hexdigest() != MANIFEST_SHA:
        raise RuntimeError("v5 manifest bytes changed")
    for proc in Path("/proc").iterdir():
        if proc.name.isdigit():
            try:
                command = (proc / "cmdline").read_bytes()
            except (OSError, PermissionError):
                continue
            if str(TARGET).encode() in command:
                raise RuntimeError(f"v5 still referenced by process {proc.name}")
    shutil.rmtree(TARGET)
    print(json.dumps({"status": "REMOVED_ISOLATED_V5_AFTER_ARCHIVE_AND_LOG_BACKUP",
                      "path": str(TARGET), "archive_sha256": ARCHIVE_SHA}), flush=True)
    print("M327_V5_INSTALL_REMOVED_PASS", flush=True)


if __name__ == "__main__":
    main()
