#!/usr/bin/env python3
"""Import-only release-path probe; no overlay, model, service or inference."""

import importlib
import json
import os
from pathlib import Path
import sys


ROOT = Path("/home/ubuntu/tellme_release_install_20260926")
BASE = ROOT / "deployment/mage_vl4b"
DIRS = [
    BASE / "m254_dual_path_web_candidate",
    BASE / "m243_web_prefill_board_candidate",
    BASE / "m242_m241_fixed_text_board_candidate",
    BASE / "m238_input_prefetch_board_candidate",
    BASE / "m241_grouped_gqa_board_candidate",
    BASE / "m231_parse_reuse_board_candidate",
    ROOT / "tmp/m227_runtime_base/m227_runtime_base_patch",
    ROOT / "tmp/m223_realtime/m223_realtime_delta",
    ROOT / "tmp/m218_dual_source/m218_dual_source_delta",
    BASE / "m181_m120_video_board_candidate/text_runtime",
    BASE / "m181_m120_video_board_candidate/ps_vision_payload",
    BASE / "m181_m120_video_board_candidate",
    BASE / "m175_m120_fixed_text_candidate/runtime",
    BASE / "m175_m120_fixed_text_candidate/runtime/support",
]
if not all(path.is_dir() for path in DIRS):
    raise RuntimeError("module directory closure missing")
os.environ["XILINX_XRT"] = "/usr"
os.environ["TMPDIR"] = "/dev/shm"
os.environ["TRANSFORMERS_OFFLINE"] = "1"
os.environ["HF_HUB_OFFLINE"] = "1"
sys.path[:0] = [str(path) for path in DIRS]
module = importlib.import_module("m254_video_server")
paths = {name: str(sys.modules[name].__file__) for name in (
    "m254_video_server", "m243_video_server", "m238_prefill_runtime", "board_runtime", "video_server"
)}
if any(not Path(path).is_relative_to(ROOT) for path in paths.values()):
    raise RuntimeError("import resolved outside release root")
print(json.dumps({"status": "PASS_IMPORT_ONLY", "paths": paths}, indent=2), flush=True)
print("M327_SERVICE_IMPORT_PROBE_PASS", flush=True)
