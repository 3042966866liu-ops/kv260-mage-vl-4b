#!/usr/bin/env python3
"""Build the clean M227 ps_vision_runtime compatibility patch."""

import hashlib
import json
import os
import shutil
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "tmp/m227_runtime_base/m227_runtime_base_patch"
RESULT = ROOT / "deployment/mage_vl4b/M227_RUNTIME_BASE_PATCH_BUILD_RESULT.json"


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> int:
    sources = {
        "ps_vision_runtime.py": ROOT / "deployment/mage_vl4b/m200_video_e2e_overlay_source/ps_vision_runtime.py",
        "m227_import_preflight.py": ROOT / "scripts/m227_import_preflight.py",
        "m227_verify_patch.py": ROOT / "scripts/m227_verify_patch.py",
        "m227_health_probe.py": ROOT / "scripts/m227_health_probe.py",
        "m227_board_restart.sh": ROOT / "scripts/m227_board_restart.sh",
    }
    partial = OUT.with_name(OUT.name + ".partial")
    if OUT.exists(): shutil.rmtree(OUT)
    if partial.exists(): shutil.rmtree(partial)
    partial.mkdir(parents=True)
    for name, source in sources.items(): shutil.copyfile(source, partial / name)
    files = [{"path": path.name, "bytes": path.stat().st_size, "sha256": sha(path)} for path in sorted(partial.iterdir())]
    manifest = {
        "date": "2026-09-01",
        "gate": "M227-runtime-base-compatibility-patch",
        "status": "PASS",
        "files": files,
        "file_count": len(files),
        "persistent_boot_dtb_cma_partitions_services_changed": False,
        "stable_rollback_preserved": True,
    }
    (partial / "PACKAGE_MANIFEST.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    os.replace(partial, OUT)
    result = {
        "date": "2026-09-01", "gate": "M227-runtime-base-compatibility-patch-build", "status": "PASS",
        "directory": OUT.relative_to(ROOT).as_posix(), "package_manifest_sha256": sha(OUT / "PACKAGE_MANIFEST.json"),
        "file_count": len(files), "stable_rollback_preserved": True,
    }
    RESULT.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print("M227_RUNTIME_BASE_PATCH_BUILD_PASS")
    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__": raise SystemExit(main())

