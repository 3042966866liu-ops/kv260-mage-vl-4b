#!/usr/bin/env python3
"""Build a clean, hash-locked offline ARM64 Mage-VL runtime bundle."""

from __future__ import annotations

import hashlib
import json
import os
import shutil
import stat
import sys
import zipfile
from email.parser import Parser
from pathlib import Path, PurePosixPath


sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parents[1]
TORCH_SOURCE = ROOT / "tmp/m189_torch_arm64"
ML_SOURCE = ROOT / "tmp/m189_resolved_arm64"
OUTPUT = ROOT / "deployment/mage_vl4b/m189_arm64_mage_runtime_bundle"
RESULT = ROOT / "deployment/mage_vl4b/M189_ARM64_TORCH_BUNDLE_RESULT.json"
TORCH_EXPECTED = {
    "torch-2.12.1+cpu-cp310-cp310-manylinux_2_28_aarch64.whl",
    "setuptools-81.0.0-py3-none-any.whl",
    "filelock-3.32.5-py3-none-any.whl",
    "typing_extensions-4.16.0-py3-none-any.whl",
    "sympy-1.14.0-py3-none-any.whl",
    "mpmath-1.3.0-py3-none-any.whl",
    "networkx-3.4.2-py3-none-any.whl",
    "jinja2-3.1.6-py3-none-any.whl",
    "fsspec-2026.7.0-py3-none-any.whl",
    "markupsafe-3.0.3-cp310-cp310-manylinux2014_aarch64.manylinux_2_17_aarch64.manylinux_2_28_aarch64.whl",
}
ML_EXPECTED = {
    "annotated_doc-0.0.5-py3-none-any.whl",
    "anyio-4.14.2-py3-none-any.whl",
    "certifi-2026.7.22-py3-none-any.whl",
    "click-8.5.0-py3-none-any.whl",
    "colorama-0.4.6-py2.py3-none-any.whl",
    "filelock-3.32.5-py3-none-any.whl",
    "fsspec-2026.7.0-py3-none-any.whl",
    "h11-0.16.0-py3-none-any.whl",
    "hf_xet-1.6.1a0-cp38-abi3-manylinux_2_28_aarch64.whl",
    "httpcore-1.0.9-py3-none-any.whl",
    "httpx-0.28.1-py3-none-any.whl",
    "huggingface_hub-1.29.0-py3-none-any.whl",
    "idna-3.19-py3-none-any.whl",
    "markdown_it_py-4.2.0-py3-none-any.whl",
    "mdurl-0.1.2-py3-none-any.whl",
    "numpy-1.26.4-cp310-cp310-manylinux_2_17_aarch64.manylinux2014_aarch64.whl",
    "packaging-26.3-py3-none-any.whl",
    "pygments-2.21.0-py3-none-any.whl",
    "pyyaml-6.0.3-cp310-cp310-manylinux2014_aarch64.manylinux_2_17_aarch64.manylinux_2_28_aarch64.whl",
    "regex-2026.9.3-cp310-cp310-manylinux2014_aarch64.manylinux_2_17_aarch64.manylinux_2_28_aarch64.whl",
    "rich-15.0.0-py3-none-any.whl",
    "safetensors-0.8.0-cp310-abi3-manylinux_2_17_aarch64.manylinux2014_aarch64.whl",
    "shellingham-1.5.4-py2.py3-none-any.whl",
    "tokenizers-0.22.1-cp39-abi3-manylinux_2_17_aarch64.manylinux2014_aarch64.whl",
    "tqdm-4.70.0-py3-none-any.whl",
    "transformers-5.7.0-py3-none-any.whl",
    "typer-0.27.2-py3-none-any.whl",
    "typing_extensions-4.16.0-py3-none-any.whl",
}
# Three pure-Python dependencies are shared by both resolved closures.
SHARED = {
    "filelock-3.32.5-py3-none-any.whl",
    "fsspec-2026.7.0-py3-none-any.whl",
    "typing_extensions-4.16.0-py3-none-any.whl",
}
EXPECTED = TORCH_EXPECTED | ML_EXPECTED
TORCH_SHA = "93b8ceb3689e34a92465d4cac7d08e65dfcf49d10d6d47d15db5f3917baa1152"


def sha256(path: Path) -> str:
    value = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(32 << 20), b""):
            value.update(block)
    return value.hexdigest()


def inspect_wheel(path: Path) -> dict:
    with zipfile.ZipFile(path) as archive:
        bad = archive.testzip()
        if bad is not None:
            raise RuntimeError(f"M189 corrupt wheel member: {path.name}:{bad}")
        infos = archive.infolist()
        for info in infos:
            parts = PurePosixPath(info.filename).parts
            mode = info.external_attr >> 16
            if not parts or parts[0] in {"", "."} or ".." in parts or stat.S_ISLNK(mode):
                raise RuntimeError(f"M189 unsafe wheel member: {path.name}:{info.filename}")
        metadata_name = next(name for name in archive.namelist() if name.endswith(".dist-info/METADATA"))
        wheel_name = next(name for name in archive.namelist() if name.endswith(".dist-info/WHEEL"))
        metadata = Parser().parsestr(archive.read(metadata_name).decode("utf-8"))
        wheel_lines = archive.read(wheel_name).decode("utf-8").splitlines()
        tags = [line.split(":", 1)[1].strip() for line in wheel_lines if line.startswith("Tag:")]
        if not tags or not all(tag.endswith("-any") or "aarch64" in tag for tag in tags):
            raise RuntimeError(f"M189 incompatible wheel tag: {path.name}:{tags}")
        return {
            "path": path.name,
            "bytes": path.stat().st_size,
            "sha256": sha256(path),
            "distribution": metadata["Name"],
            "version": metadata["Version"],
            "tags": tags,
            "unpacked_bytes": sum(info.file_size for info in infos),
            "member_count": len(infos),
            "requires_dist": metadata.get_all("Requires-Dist") or [],
        }


def main() -> int:
    torch_actual = {path.name for path in TORCH_SOURCE.glob("*.whl")}
    ml_actual = {path.name for path in ML_SOURCE.glob("*.whl")}
    if torch_actual != TORCH_EXPECTED:
        raise RuntimeError(
            f"M189 torch closure mismatch missing={sorted(TORCH_EXPECTED-torch_actual)} "
            f"extra={sorted(torch_actual-TORCH_EXPECTED)}"
        )
    if ml_actual != ML_EXPECTED:
        raise RuntimeError(
            f"M189 ML closure mismatch missing={sorted(ML_EXPECTED-ml_actual)} "
            f"extra={sorted(ml_actual-ML_EXPECTED)}"
        )
    for name in SHARED:
        if sha256(TORCH_SOURCE / name) != sha256(ML_SOURCE / name):
            raise RuntimeError(f"M189 shared wheel identity mismatch: {name}")
    if OUTPUT.exists() or OUTPUT.with_name(OUTPUT.name + ".partial").exists():
        raise RuntimeError("M189 clean output required")
    staging = OUTPUT.with_name(OUTPUT.name + ".partial")
    staging.mkdir(parents=True)
    records = []
    for name in sorted(EXPECTED):
        source = ML_SOURCE / name if name in ML_EXPECTED else TORCH_SOURCE / name
        target = staging / name
        shutil.copyfile(source, target)
        records.append(inspect_wheel(target))
    torch = next(item for item in records if item["distribution"].lower() == "torch")
    if torch["sha256"] != TORCH_SHA or torch["version"] != "2.12.1+cpu" or torch["tags"] != ["cp310-cp310-manylinux_2_28_aarch64"]:
        raise RuntimeError("M189 exact torch identity mismatch")
    distributions = {item["distribution"].lower().replace("-", "_") for item in records}
    required = {
        "annotated_doc", "anyio", "certifi", "click", "colorama", "filelock", "fsspec", "h11",
        "hf_xet", "httpcore", "httpx", "huggingface_hub", "idna", "jinja2", "markdown_it_py",
        "markupsafe", "mdurl", "mpmath", "networkx", "numpy", "packaging", "pygments", "pyyaml",
        "regex", "rich", "safetensors", "setuptools", "shellingham", "sympy", "tokenizers", "torch",
        "tqdm", "transformers", "typer", "typing_extensions",
    }
    if distributions != required:
        raise RuntimeError("M189 resolved distribution closure mismatch")
    manifest = {
        "date": "2026-09-01",
        "gate": "M189-KV260-ARM64-Mage-VL-offline-runtime-bundle",
        "status": "PASS_OFFLINE_BUNDLE",
        "target": {"machine": "aarch64", "python": "3.10", "glibc_minimum": "2.28", "board_os": "Ubuntu 22.04"},
        "locked_runtime": {
            "torch": "2.12.1+cpu",
            "transformers": "5.7.0",
            "huggingface_hub": "1.29.0",
            "safetensors": "0.8.0",
            "tokenizers": "0.22.1",
            "numpy": "1.26.4",
        },
        "torch": {"version": "2.12.1+cpu", "wheel_sha256": TORCH_SHA, "source": "https://download.pytorch.org/whl/cpu"},
        "files": records,
        "file_count": len(records),
        "total_bytes": sum(item["bytes"] for item in records),
        "total_unpacked_bytes": sum(item["unpacked_bytes"] for item in records),
        "install_policy": "isolated --target directory; never modify system/PYNQ site-packages",
    }
    manifest_path = staging / "BUNDLE_MANIFEST.json"
    manifest_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    ready = {"status": "READY", "bundle_manifest_sha256": sha256(manifest_path), "file_count": len(records)}
    (staging / "BUNDLE_READY.json").write_text(json.dumps(ready, indent=2) + "\n", encoding="utf-8")
    os.replace(staging, OUTPUT)
    result = {
        "date": "2026-09-01",
        "gate": "M189-KV260-ARM64-Mage-VL-offline-runtime-bundle-build",
        "status": "PASS",
        "classification": "Offline ARM64 Mage-VL runtime wheel bundle only; not transferred or installed on the board.",
        "directory": OUTPUT.relative_to(ROOT).as_posix(),
        "bundle_manifest_sha256": sha256(OUTPUT / "BUNDLE_MANIFEST.json"),
        "torch_wheel_sha256": TORCH_SHA,
        "file_count": len(records),
        "total_bytes": manifest["total_bytes"],
        "total_unpacked_bytes": manifest["total_unpacked_bytes"],
        "m188_inventory": "deployment/mage_vl4b/M188_BOARD_ML_RUNTIME_INVENTORY_RESULT_01.json",
        "board_state_changed": False,
        "stable_rollback_preserved": True,
    }
    temporary = RESULT.with_name(RESULT.name + ".partial")
    temporary.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    os.replace(temporary, RESULT)
    print(json.dumps(result, indent=2))
    print("M189_ARM64_TORCH_BUNDLE_BUILD_PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
