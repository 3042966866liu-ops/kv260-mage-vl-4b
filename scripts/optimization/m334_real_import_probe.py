#!/usr/bin/env python3
"""Read-only KV260 import closure for the real M333/M254 Web entry.

This diagnostic neither constructs a model nor loads an FPGA overlay.  It
intentionally uses the installed release's module precedence, then imports
the actual M333 entry instead of a fake m254 module.
"""

from __future__ import annotations

import hashlib
import importlib
import json
import os
from pathlib import Path
import sys
import time
import traceback


ROOT = Path("/home/ubuntu/tellme_release_install_20260926")
STABLE = ROOT / "deployment/mage_vl4b"
M181 = STABLE / "m181_m120_video_board_candidate"
M175 = STABLE / "m175_m120_fixed_text_candidate"
M333 = Path("/home/ubuntu/m333_offline_board_01/deployment/m333")
RESULT = Path("/home/ubuntu/m334_import_probe_01/RESULT.json")


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def main() -> int:
    sys.dont_write_bytecode = True
    started = time.monotonic()
    value: dict = {
        "gate": "M334-KV260-real-M333-import-closure",
        "status": "FAIL",
        "classification": "read-only import; no model, detector, overlay or Web request",
        "overlay_loaded": False,
        "stable_service_modified": False,
        "release_root": str(ROOT),
        "m333_root": str(M333),
        "euid": os.geteuid(),
    }
    try:
        if os.geteuid() == 0:
            raise RuntimeError("read-only import probe must run as ubuntu")
        if not ROOT.is_dir() or not M333.is_dir():
            raise FileNotFoundError("release or M333 source root missing")
        dirs = [
            M333,
            ROOT / "runtime_site",
            STABLE / "m254_dual_path_web_candidate",
            STABLE / "m243_web_prefill_board_candidate",
            STABLE / "m242_m241_fixed_text_board_candidate",
            STABLE / "m238_input_prefetch_board_candidate",
            STABLE / "m241_grouped_gqa_board_candidate",
            STABLE / "m231_parse_reuse_board_candidate",
            ROOT / "tmp/m227_runtime_base/m227_runtime_base_patch",
            ROOT / "tmp/m223_realtime/m223_realtime_delta",
            ROOT / "tmp/m218_dual_source/m218_dual_source_delta",
            M181 / "text_runtime",
            M181 / "ps_vision_payload",
            M181,
            M175 / "runtime",
            M175 / "runtime/support",
        ]
        missing = [str(path) for path in dirs if not path.is_dir()]
        if missing:
            raise FileNotFoundError("module path closure missing: " + ", ".join(missing))
        sys.path[:0] = [str(path) for path in dirs]
        identity = {}
        for name, expected_dir in (
            ("m333_review_bridge", M333),
            ("m254_video_server", STABLE / "m254_dual_path_web_candidate"),
            ("m333_video_server", M333),
        ):
            print("M334_IMPORT_BEGIN", name, flush=True)
            module = importlib.import_module(name)
            source = Path(module.__file__).resolve()
            if source.parent != expected_dir.resolve():
                raise RuntimeError(f"{name} resolved outside expected directory: {source}")
            identity[name] = {"path": str(source), "sha256": sha256(source)}
            print("M334_IMPORT_PASS", name, flush=True)
        import video_server

        if video_server.LiveController is not sys.modules["m333_video_server"].M333DualPathController:
            raise RuntimeError("real video_server controller is not M333")
        value.update({"status": "PASS", "imports": identity,
                      "real_controller_bound": True})
    except BaseException as error:
        value.update({"error": f"{type(error).__name__}: {error}",
                      "traceback": traceback.format_exc()})
    value["elapsed_s"] = time.monotonic() - started
    RESULT.parent.mkdir(parents=True, exist_ok=True)
    temporary = RESULT.with_suffix(".json.tmp")
    temporary.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    os.replace(temporary, RESULT)
    print("M334_IMPORT_RESULT", json.dumps(value, ensure_ascii=False), flush=True)
    return 0 if value["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
