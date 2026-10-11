#!/usr/bin/env python3
"""Read-only scan of the exact local wheels for PIL.Image.Resampling uses."""

from pathlib import Path
import zipfile


ROOT = Path(__file__).resolve().parents[1]
WHEELS = (
    ROOT / "deployment/mage_vl4b/m189_arm64_mage_runtime_bundle/transformers-5.7.0-py3-none-any.whl",
    ROOT / "deployment/mage_vl4b/m249_ssdlite_board_candidate/wheels/torchvision-0.27.1+cpu-cp310-cp310-manylinux_2_28_aarch64.whl",
)


for wheel in WHEELS:
    with zipfile.ZipFile(wheel) as archive:
        for name in archive.namelist():
            if name.endswith(".py"):
                for line_no, line in enumerate(archive.read(name).decode("utf-8", errors="replace").splitlines(), 1):
                    if "Image.Resampling" in line:
                        print(f"{wheel.name}:{name}:{line_no}: {line.strip()}")
