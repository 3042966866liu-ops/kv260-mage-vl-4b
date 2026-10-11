#!/usr/bin/env python3
"""Read-only Pillow and isolated dependency identity probe for M327."""

import json
import os
from pathlib import Path
import sys


ROOT = Path("/home/ubuntu/tellme_release_install_20260926")
SITE = ROOT / "runtime_site"


def main():
    if os.geteuid() != 0 or not SITE.is_dir():
        raise RuntimeError("root and isolated runtime_site required")
    sys.path.insert(0, str(SITE))
    import PIL
    from PIL import Image
    import torch
    import torchvision
    result = {
        "status": "MEASURED_NO_MODEL_RUN",
        "pillow_version": PIL.__version__,
        "pillow_origin": str(Path(PIL.__file__).resolve()),
        "image_origin": str(Path(Image.__file__).resolve()),
        "image_has_resampling": hasattr(Image, "Resampling"),
        "image_has_lanczos": hasattr(Image, "LANCZOS"),
        "torch_version": torch.__version__,
        "torch_origin": str(Path(torch.__file__).resolve()),
        "torchvision_version": torchvision.__version__,
        "torchvision_origin": str(Path(torchvision.__file__).resolve()),
    }
    print(json.dumps(result, sort_keys=True), flush=True)
    print("M327_PILLOW_PROBE_MEASURED", flush=True)


if __name__ == "__main__":
    main()
