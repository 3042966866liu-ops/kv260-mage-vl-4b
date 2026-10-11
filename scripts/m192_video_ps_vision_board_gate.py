#!/usr/bin/env python3
"""Rerun the fixed four-frame PS vision gate with the isolated M190 runtime."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import platform
import subprocess
import sys
import time
from pathlib import Path


sys.dont_write_bytecode = True
PACKAGE_SHA = "1596536bfe6865cb7eab5c038d8b4da8b666afc7cbd629ddc4559781727151d6"
M184_SHA = "790bae8a261156e95b23d7aa349d9410dc3d511388a94ad9be80106ce8a2cf84"
BUNDLE_SHA = "88c3fefaae94a475751bef3348e0048f30fc90bb1f27caa20e79f2e0f77361ba"
ROOT = Path("/home/ubuntu/tellme_m120_m89x2_20260901")
CANDIDATE = ROOT / "m181_m120_video_board_candidate"
SITE_PACKAGES = ROOT / "m190_mage_runtime"
RAW_RESULT = ROOT / "results/M192_M181_PS_VISION_RAW_RESULT.json"


def sha256(path: Path) -> str:
    value = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(32 << 20), b""):
            value.update(block)
    return value.hexdigest()


def atomic_json(path: Path, value: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + f".partial-{os.getpid()}")
    temporary.write_text(json.dumps(value, indent=2) + "\n", encoding="utf-8")
    os.replace(temporary, path)


def required_members(manifest: dict) -> list[str]:
    fixed = [
        "ps_vision_runtime.py", "test_ps_vision_runtime.py",
        "fixtures/official_four_frame_processor.npz", "fixtures/m56_w4_vision_merged_cpu_bf16.npz",
        "auxiliary/M90_VISION_RAW_AUX_MANIFEST.json", "auxiliary/m90_vision_raw_bf16.bin",
        "ps_vision_payload/PAYLOAD_MANIFEST.json", "vision_layout/SIXPORT_LAYOUT_MANIFEST.json",
    ]
    fixed.extend(item["path"] for item in manifest["files"] if item["path"].startswith("ps_vision_payload/"))
    fixed.extend(item["path"] for item in manifest["files"] if item["path"].startswith("vision_layout/weights"))
    return sorted(set(fixed))


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--candidate", type=Path, required=True)
    parser.add_argument("--m184-result", type=Path, required=True)
    parser.add_argument("--m190-result", type=Path, required=True)
    parser.add_argument("--expected-m190-sha256", required=True)
    parser.add_argument("--result", type=Path, required=True)
    args = parser.parse_args()
    started = time.monotonic()
    result = {
        "date": "2026-09-01",
        "gate": "M192-M181-fixed-four-frame-PS-vision-isolated-runtime-numerical",
        "status": "FAIL",
        "classification": "Real-KV260 PS vision numerical gate only; not FPGA video-language E2E, performance or Web evidence.",
        "candidate_build_id": "0x4D395832",
        "package_manifest_sha256": PACKAGE_SHA,
        "m184_formal_result_sha256": M184_SHA,
        "m193_formal_result_sha256": args.expected_m190_sha256,
        "thresholds": {"cosine_minimum": 0.999, "rmse_maximum": 0.05},
        "boot_dtb_cma_partitions_services_changed": False,
        "stable_rollback_preserved": True,
    }
    try:
        candidate = args.candidate.resolve()
        if candidate != CANDIDATE or args.result.resolve().parent != ROOT / "results":
            raise RuntimeError("M192 fixed path identity mismatch")
        if platform.machine().lower() not in {"aarch64", "arm64"}:
            raise RuntimeError(f"M192 requires aarch64, observed={platform.machine()}")
        if len(args.expected_m190_sha256) != 64 or sha256(args.m190_result) != args.expected_m190_sha256:
            raise RuntimeError("M192 exact M193 result hash mismatch")
        m193 = json.loads(args.m190_result.read_text())
        if m193.get("status") != "PASS" or m193.get("pillow_wheel_sha256") != "a40905599d8079e09f25027423aed94f2823adaf2868940de991e53a449e14a8":
            raise RuntimeError("M192 M193 predecessor is not the accepted runtime PASS")
        if Path(m193.get("isolated_site_packages", "")).resolve() != SITE_PACKAGES or not SITE_PACKAGES.is_dir():
            raise RuntimeError("M192 isolated runtime identity mismatch")
        if sha256(args.m184_result) != M184_SHA:
            raise RuntimeError("M192 exact M184 predecessor mismatch")
        m184 = json.loads(args.m184_result.read_text())
        if m184.get("status") != "PASS" or m184.get("package_manifest_sha256") != PACKAGE_SHA:
            raise RuntimeError("M192 M184 predecessor is not PASS")
        manifest_path = candidate / "PACKAGE_MANIFEST.json"
        if sha256(manifest_path) != PACKAGE_SHA:
            raise RuntimeError("M192 candidate package manifest mismatch")
        manifest = json.loads(manifest_path.read_text())
        entries = {item["path"]: item for item in manifest.get("files", [])}
        if len(entries) != 48:
            raise RuntimeError("M192 package file count mismatch")
        verified_bytes = 0
        for relative in required_members(manifest):
            item = entries.get(relative)
            path = candidate / relative
            if item is None or path.is_symlink() or not path.is_file():
                raise RuntimeError(f"M192 missing required member: {relative}")
            if path.stat().st_size != int(item["bytes"]) or sha256(path) != item["sha256"]:
                raise RuntimeError(f"M192 required member mismatch: {relative}")
            verified_bytes += int(item["bytes"])
        environment = os.environ.copy()
        environment.update({
            "PYTHONPATH": str(SITE_PACKAGES), "PYTHONDONTWRITEBYTECODE": "1",
            "TRANSFORMERS_OFFLINE": "1", "HF_HUB_OFFLINE": "1",
        })
        probe = subprocess.run(
            [sys.executable, "-c", "import json,numpy,torch,transformers,safetensors,tokenizers,huggingface_hub,pynq; print(json.dumps({'numpy':numpy.__version__,'torch':torch.__version__,'transformers':transformers.__version__,'safetensors':safetensors.__version__,'tokenizers':tokenizers.__version__,'huggingface_hub':huggingface_hub.__version__,'pynq':getattr(pynq,'__version__','present')}))"],
            env=environment, text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=180,
        )
        result["environment_probe_output"] = probe.stdout[-8000:]
        if probe.returncode != 0:
            raise RuntimeError(f"M192 isolated runtime import failed rc={probe.returncode}")
        result["environment"] = json.loads(probe.stdout.strip().splitlines()[-1])
        if result["environment"]["torch"] != "2.12.1+cpu" or result["environment"]["transformers"] != "5.7.0":
            raise RuntimeError("M192 locked runtime version mismatch")
        if RAW_RESULT.exists():
            raise RuntimeError("M192 requires absent raw result")
        command = [
            sys.executable, str(candidate / "test_ps_vision_runtime.py"),
            "--model-code", str(candidate / "ps_vision_payload"),
            "--layout", str(candidate / "vision_layout"),
            "--raw-manifest", str(candidate / "auxiliary/M90_VISION_RAW_AUX_MANIFEST.json"),
            "--processor-fixture", str(candidate / "fixtures/official_four_frame_processor.npz"),
            "--golden", str(candidate / "fixtures/m56_w4_vision_merged_cpu_bf16.npz"),
            "--result", str(RAW_RESULT),
        ]
        vision_started = time.monotonic()
        completed = subprocess.run(command, cwd=candidate, env=environment, text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=5400)
        result["vision_wall_ms"] = (time.monotonic() - vision_started) * 1000
        result["test_exit_code"] = completed.returncode
        result["test_output_tail"] = completed.stdout[-12000:]
        if not RAW_RESULT.is_file():
            raise RuntimeError("M192 raw numerical result missing")
        raw = json.loads(RAW_RESULT.read_text())
        result["raw_result"] = raw
        metrics = raw.get("metrics_vs_M56_W4_BF16_golden", {})
        cosine = float(metrics.get("cosine_similarity", float("nan")))
        rmse = float(metrics.get("rmse", float("nan")))
        if completed.returncode != 0 or raw.get("status") != "PASS":
            raise RuntimeError("M192 underlying PS vision gate failed")
        if raw.get("output_shape") != [784, 2560] or not math.isfinite(cosine) or not math.isfinite(rmse) or cosine < 0.999 or rmse > 0.05:
            raise RuntimeError("M192 frozen numerical threshold mismatch")
        result.update({
            "status": "PASS", "output_shape": raw["output_shape"],
            "metrics_vs_same_method_CPU_PS_golden": metrics,
            "vision_execution_device": "KV260 Cortex-A53 PS", "fpga_language_executed": False,
            "web_deployed": False,
            "required_member_bytes_rehashed": verified_bytes,
            "next_gate": "Run fixed four-frame video-language E2E with the inherited M120 FPGA language/head path.",
        })
    except BaseException as error:
        result["error"] = f"{type(error).__name__}: {error}"
        result["fpga_language_executed"] = False
        result["web_deployed"] = False
        result["next_gate"] = "Repair and rerun only M192 PS vision; do not run FPGA video-language E2E."
    finally:
        result["total_ms"] = (time.monotonic() - started) * 1000
        atomic_json(args.result.resolve(), result)
    print("__M192_PS_VISION_RESULT_BEGIN__", flush=True)
    print(json.dumps(result, separators=(",", ":")), flush=True)
    print("__M192_PS_VISION_RESULT_END__", flush=True)
    print("M192_M181_PS_VISION_BOARD_PASS" if result["status"] == "PASS" else "M192_M181_PS_VISION_BOARD_FAIL", flush=True)
    return 0 if result["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
