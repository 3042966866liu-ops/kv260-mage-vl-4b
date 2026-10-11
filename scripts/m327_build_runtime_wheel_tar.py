#!/usr/bin/env python3
"""Create a deterministic, hash-verified local ARM64 wheel bundle for M327."""

import argparse
import hashlib
import json
from pathlib import Path
import tarfile


ROOT = Path(__file__).resolve().parents[1]
M189 = ROOT / "deployment/mage_vl4b/m189_arm64_mage_runtime_bundle"
TV = ROOT / "deployment/mage_vl4b/m249_ssdlite_board_candidate/wheels/torchvision-0.27.1+cpu-cp310-cp310-manylinux_2_28_aarch64.whl"
TV_SHA = "3323edb900ca46d29dba267ee809e55fe5fe09cd3d9f54124a7c5ed33a6a2dbe"


def digest(path):
    h = hashlib.sha256()
    with path.open("rb") as source:
        for block in iter(lambda: source.read(4 << 20), b""):
            h.update(block)
    return h.hexdigest()


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--output", required=True, type=Path)
    args = p.parse_args()
    output = args.output.resolve()
    if output.exists():
        raise RuntimeError("refusing to overwrite a wheel archive")
    manifest_path = M189 / "BUNDLE_MANIFEST.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if manifest.get("file_count") != 35 or len(manifest["files"]) != 35:
        raise RuntimeError("unexpected M189 wheel count")
    entries = [("BUNDLE_MANIFEST.json", manifest_path)]
    for item in manifest["files"]:
        name = item["path"]
        if Path(name).name != name or not name.endswith(".whl"):
            raise RuntimeError("unsafe wheel path")
        path = M189 / name
        if path.stat().st_size != item["bytes"] or digest(path) != item["sha256"]:
            raise RuntimeError(f"M189 wheel identity failed: {name}")
        entries.append(("wheels/" + name, path))
    if digest(TV) != TV_SHA:
        raise RuntimeError("torchvision wheel identity failed")
    entries.append(("wheels/" + TV.name, TV))
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("xb") as stream, tarfile.open(fileobj=stream, mode="w") as tar:
        for name, path in entries:
            info = tarfile.TarInfo(name)
            info.size = path.stat().st_size
            info.mode = 0o644
            info.mtime = 0
            with path.open("rb") as source:
                tar.addfile(info, source)
    result = {"status": "PASS_LOCAL_RUNTIME_WHEEL_BUNDLE", "path": str(output),
              "bytes": output.stat().st_size, "sha256": digest(output),
              "wheel_count": 36, "m189_manifest_sha256": digest(manifest_path),
              "torchvision_sha256": TV_SHA}
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
