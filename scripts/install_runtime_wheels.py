#!/usr/bin/env python3
"""Install the locked ARM64 Torch/Mage runtime into this release, never stable."""

from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import platform
import shutil
import subprocess
import sys
import tarfile
import tempfile
import time


ROOT = Path(__file__).resolve().parents[1]
ARCHIVE = ROOT / "external_assets/runtime_wheels/m327_runtime_wheels_20260926.tar"
ARCHIVE_SHA = "5b414672750e1e62ebbe6360e96a3a991a293d8da3dd9fa292eb8a29d0b07c96"
M189_SHA = "88c3fefaae94a475751bef3348e0048f30fc90bb1f27caa20e79f2e0f77361ba"
TV_NAME = "torchvision-0.27.1+cpu-cp310-cp310-manylinux_2_28_aarch64.whl"
TV_SHA = "3323edb900ca46d29dba267ee809e55fe5fe09cd3d9f54124a7c5ed33a6a2dbe"
PIL_WHEEL = ROOT / "external_assets/runtime_wheels/pillow-12.1.0-cp310-cp310-manylinux2014_aarch64.manylinux_2_17_aarch64.whl"
PIL_SHA = "a40905599d8079e09f25027423aed94f2823adaf2868940de991e53a449e14a8"
SITE = ROOT / "runtime_site"
PARTIAL = ROOT / "runtime_site.partial"
RESULT = ROOT / "results/m327_runtime_install.json"
PYTHON = Path("/usr/local/share/pynq-venv/bin/python3")


def digest(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as source:
        for block in iter(lambda: source.read(4 << 20), b""):
            h.update(block)
    return h.hexdigest()


def save_result(data: dict) -> None:
    RESULT.parent.mkdir(parents=True, exist_ok=True)
    tmp = RESULT.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    os.replace(tmp, RESULT)


def extract_verified(temp: Path) -> list[Path]:
    with tarfile.open(ARCHIVE, "r:") as tar:
        members = tar.getmembers()
        names = {member.name for member in members}
        expected_prefix = "wheels/"
        if len(members) != 37 or len(names) != 37 or "BUNDLE_MANIFEST.json" not in names:
            raise RuntimeError("runtime wheel archive member count/identity mismatch")
        for member in members:
            if (not member.isfile() or member.name.startswith("/") or ".." in Path(member.name).parts
                    or (member.name != "BUNDLE_MANIFEST.json" and not member.name.startswith(expected_prefix))):
                raise RuntimeError(f"unsafe runtime wheel archive member: {member.name}")
            target = temp / member.name
            target.parent.mkdir(parents=True, exist_ok=True)
            with tar.extractfile(member) as source, target.open("xb") as out:
                shutil.copyfileobj(source, out, length=4 << 20)
            if target.stat().st_size != member.size:
                raise RuntimeError(f"runtime wheel size mismatch: {member.name}")
    manifest_path = temp / "BUNDLE_MANIFEST.json"
    if digest(manifest_path) != M189_SHA:
        raise RuntimeError("M189 bundle manifest SHA mismatch")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if manifest.get("file_count") != 35 or len(manifest["files"]) != 35:
        raise RuntimeError("M189 wheel count mismatch")
    expected = {"BUNDLE_MANIFEST.json", expected_prefix + TV_NAME}
    wheels = []
    for item in manifest["files"]:
        name = item["path"]
        if Path(name).name != name or not name.endswith(".whl"):
            raise RuntimeError("invalid M189 wheel path")
        path = temp / expected_prefix / name
        expected.add(expected_prefix + name)
        if path.stat().st_size != item["bytes"] or digest(path) != item["sha256"]:
            raise RuntimeError(f"M189 wheel hash mismatch: {name}")
        wheels.append(path)
    if names != expected or digest(temp / expected_prefix / TV_NAME) != TV_SHA:
        raise RuntimeError("runtime archive has missing/extra wheel or torchvision hash mismatch")
    wheels.append(temp / expected_prefix / TV_NAME)
    return wheels


def main() -> int:
    record = {"gate": "M327-isolated-runtime-wheel-install", "status": "FAIL",
              "install_root": str(ROOT), "bundle_sha256": ARCHIVE_SHA}
    try:
        if (os.geteuid() != 0 or subprocess.run(["sudo", "-n", "true"], check=False).returncode != 0
                or Path(sys.executable).resolve() != PYTHON.resolve()):
            raise RuntimeError("same-terminal root and PYNQ Python required")
        if platform.machine().lower() not in ("aarch64", "arm64") or sys.version_info[:2] != (3, 10):
            raise RuntimeError("requires KV260 AArch64 Python 3.10")
        if SITE.exists() or PARTIAL.exists() or SITE.is_symlink() or PARTIAL.is_symlink():
            raise RuntimeError("runtime target already exists; refusing overwrite")
        if shutil.disk_usage(ROOT).free < 1_500_000_000:
            raise RuntimeError("insufficient disk headroom for isolated runtime")
        if ARCHIVE.stat().st_size != 200151040 or digest(ARCHIVE) != ARCHIVE_SHA:
            raise RuntimeError("runtime wheel archive hash mismatch")
        if PIL_WHEEL.stat().st_size != 6222593 or digest(PIL_WHEEL) != PIL_SHA:
            raise RuntimeError("M193 Pillow wheel hash mismatch")
        start = time.monotonic()
        with tempfile.TemporaryDirectory(prefix="m327-wheels-", dir="/dev/shm") as temp_name:
            wheels = extract_verified(Path(temp_name))
            wheels.append(PIL_WHEEL)
            PARTIAL.mkdir()
            command = [str(PYTHON), "-m", "pip", "install", "--no-index", "--no-deps",
                       "--no-cache-dir", "--no-compile", "--target", str(PARTIAL)]
            completed = subprocess.run(command + [str(path) for path in wheels],
                                       text=True, stdout=subprocess.PIPE,
                                       stderr=subprocess.STDOUT, timeout=1800, check=False)
            record["pip_output_tail"] = completed.stdout[-6000:]
            if completed.returncode != 0:
                raise RuntimeError(f"isolated pip installation failed rc={completed.returncode}")
        smoke = r'''import json,numpy,torch,torchvision,transformers,safetensors,tokenizers,PIL
from PIL import Image
from torchvision.ops import nms
assert torch.__version__ == "2.12.1+cpu" and torchvision.__version__ == "0.27.1+cpu"
assert numpy.__version__ == "1.26.4" and transformers.__version__ == "5.7.0"
assert PIL.__version__ == "12.1.0" and hasattr(Image,"Resampling")
assert nms(torch.tensor([[0.,0.,2.,2.]]),torch.tensor([.9]),.5).numel() == 1
print(json.dumps({"torch":torch.__version__,"torchvision":torchvision.__version__,"numpy":numpy.__version__,"transformers":transformers.__version__,"Pillow":PIL.__version__,"safetensors":safetensors.__version__,"tokenizers":tokenizers.__version__}))'''
        env = os.environ.copy()
        env.update({"PYTHONPATH": str(PARTIAL), "PYTHONDONTWRITEBYTECODE": "1",
                    "TRANSFORMERS_OFFLINE": "1", "HF_HUB_OFFLINE": "1"})
        checked = subprocess.run([str(PYTHON), "-B", "-c", smoke], env=env,
                                 text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                                 timeout=300, check=False)
        record["smoke_output"] = checked.stdout[-6000:]
        if checked.returncode != 0:
            raise RuntimeError(f"isolated runtime native-op smoke failed rc={checked.returncode}")
        record["versions"] = json.loads(checked.stdout.strip().splitlines()[-1])
        marker = {"status": "PASS", "bundle_sha256": ARCHIVE_SHA, "pillow_sha256": PIL_SHA,
                  "python": str(PYTHON), "versions": record["versions"]}
        (PARTIAL / "RUNTIME_SITE_READY.json").write_text(
            json.dumps(marker, indent=2) + "\n", encoding="utf-8")
        os.replace(PARTIAL, SITE)
        record.update({"status": "PASS_ISOLATED_RUNTIME_INSTALLED", "site": str(SITE),
                       "wheel_count": 37, "install_seconds": time.monotonic() - start})
    except Exception as exc:
        record["error"] = f"{type(exc).__name__}: {exc}"
        if PARTIAL.is_dir() and not PARTIAL.is_symlink():
            shutil.rmtree(PARTIAL)
    save_result(record)
    print(json.dumps(record, ensure_ascii=False), flush=True)
    print("M327_RUNTIME_INSTALL_PASS" if record["status"] == "PASS_ISOLATED_RUNTIME_INSTALLED"
          else "M327_RUNTIME_INSTALL_FAIL", flush=True)
    return 0 if record["status"] == "PASS_ISOLATED_RUNTIME_INSTALLED" else 1


if __name__ == "__main__":
    raise SystemExit(main())
