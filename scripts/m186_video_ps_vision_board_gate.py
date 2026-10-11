#!/usr/bin/env python3
"""Run the fixed four-frame PS BF16/W4 vision gate on the real KV260."""

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
CANDIDATE = Path("/home/ubuntu/tellme_m120_m89x2_20260901/m181_m120_video_board_candidate")
M184_RESULT = Path("/home/ubuntu/tellme_m120_m89x2_20260901/m186_gate/M184_M181_VIDEO_BOARD_IMPORT_RESULT_01.json")
FORMAL_RESULT = Path("/home/ubuntu/tellme_m120_m89x2_20260901/results/M186_M181_PS_VISION_BOARD_RESULT.json")
RAW_RESULT = Path("/home/ubuntu/tellme_m120_m89x2_20260901/results/M186_M181_PS_VISION_RAW_RESULT.json")


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
        "ps_vision_runtime.py",
        "test_ps_vision_runtime.py",
        "fixtures/official_four_frame_processor.npz",
        "fixtures/m56_w4_vision_merged_cpu_bf16.npz",
        "auxiliary/M90_VISION_RAW_AUX_MANIFEST.json",
        "auxiliary/m90_vision_raw_bf16.bin",
        "ps_vision_payload/PAYLOAD_MANIFEST.json",
        "vision_layout/SIXPORT_LAYOUT_MANIFEST.json",
    ]
    fixed.extend(item["path"] for item in manifest["files"] if item["path"].startswith("ps_vision_payload/"))
    fixed.extend(item["path"] for item in manifest["files"] if item["path"].startswith("vision_layout/weights"))
    return sorted(set(fixed))


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--candidate", type=Path, required=True)
    parser.add_argument("--m184-result", type=Path, required=True)
    parser.add_argument("--result", type=Path, required=True)
    args = parser.parse_args()
    started = time.monotonic()
    result = {
        "date": "2026-09-01",
        "gate": "M186-M181-fixed-four-frame-PS-vision-board-numerical",
        "status": "FAIL",
        "classification": "Real-KV260 fixed-four-frame PS vision numerical gate only; not FPGA language/video E2E, performance or Web evidence.",
        "candidate_build_id": "0x4D395832",
        "package_manifest_sha256": PACKAGE_SHA,
        "m184_formal_result_sha256": M184_SHA,
        "thresholds": {"cosine_minimum": 0.999, "rmse_maximum": 0.05},
        "boot_dtb_cma_partitions_services_changed": False,
        "stable_rollback_preserved": True,
    }
    try:
        candidate = args.candidate.resolve()
        predecessor = args.m184_result.resolve()
        formal = args.result.resolve()
        if candidate != CANDIDATE or predecessor != M184_RESULT or formal != FORMAL_RESULT:
            raise RuntimeError("M186 fixed path identity mismatch")
        if platform.machine().lower() not in {"aarch64", "arm64"}:
            raise RuntimeError(f"M186 requires aarch64, observed={platform.machine()}")
        m184 = json.loads(predecessor.read_text(encoding="utf-8"))
        if sha256(predecessor) != M184_SHA or m184.get("status") != "PASS" or m184.get("package_manifest_sha256") != PACKAGE_SHA:
            raise RuntimeError("M186 exact M184 predecessor mismatch")
        manifest_path = candidate / "PACKAGE_MANIFEST.json"
        if sha256(manifest_path) != PACKAGE_SHA:
            raise RuntimeError("M186 candidate package manifest mismatch")
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        entries = {item["path"]: item for item in manifest.get("files", [])}
        if len(entries) != 48:
            raise RuntimeError("M186 package file count mismatch")
        verified_bytes = 0
        verified = required_members(manifest)
        for relative in verified:
            item = entries.get(relative)
            path = candidate / relative
            if item is None or path.is_symlink() or not path.is_file():
                raise RuntimeError(f"M186 missing required member: {relative}")
            if path.stat().st_size != int(item["bytes"]) or sha256(path) != item["sha256"]:
                raise RuntimeError(f"M186 required member hash mismatch: {relative}")
            verified_bytes += int(item["bytes"])
        forbidden = [p.relative_to(candidate).as_posix() for p in candidate.rglob("*") if p.is_file() and ("__pycache__" in p.parts or p.suffix == ".pyc" or ".partial" in p.name)]
        if forbidden:
            raise RuntimeError(f"M186 candidate cache/partial pollution: {forbidden[:4]}")
        import numpy
        import torch
        result["environment"] = {
            "architecture": platform.machine(),
            "python": sys.version.split()[0],
            "python_executable": sys.executable,
            "numpy": numpy.__version__,
            "torch": torch.__version__,
            "torch_num_threads": torch.get_num_threads(),
        }
        result["required_member_count"] = len(verified)
        result["required_member_bytes_rehashed"] = verified_bytes
        if RAW_RESULT.exists():
            raise RuntimeError("M186 requires absent raw result")
        command = [
            sys.executable,
            str(candidate / "test_ps_vision_runtime.py"),
            "--model-code", str(candidate / "ps_vision_payload"),
            "--layout", str(candidate / "vision_layout"),
            "--raw-manifest", str(candidate / "auxiliary/M90_VISION_RAW_AUX_MANIFEST.json"),
            "--processor-fixture", str(candidate / "fixtures/official_four_frame_processor.npz"),
            "--golden", str(candidate / "fixtures/m56_w4_vision_merged_cpu_bf16.npz"),
            "--result", str(RAW_RESULT),
        ]
        environment = os.environ.copy()
        environment["PYTHONDONTWRITEBYTECODE"] = "1"
        vision_started = time.monotonic()
        completed = subprocess.run(command, cwd=candidate, env=environment, text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=5400)
        result["vision_wall_ms"] = (time.monotonic() - vision_started) * 1000.0
        result["test_exit_code"] = completed.returncode
        result["test_output_tail"] = completed.stdout[-8000:]
        if not RAW_RESULT.is_file():
            raise RuntimeError("M186 raw numerical result missing")
        raw = json.loads(RAW_RESULT.read_text(encoding="utf-8"))
        result["raw_result"] = raw
        metrics = raw.get("metrics_vs_M56_W4_BF16_golden", {})
        cosine = float(metrics.get("cosine_similarity", float("nan")))
        rmse = float(metrics.get("rmse", float("nan")))
        if completed.returncode != 0 or raw.get("status") != "PASS":
            raise RuntimeError("M186 underlying PS vision numerical gate failed")
        if raw.get("output_shape") != [784, 2560] or not math.isfinite(cosine) or not math.isfinite(rmse) or cosine < 0.999 or rmse > 0.05:
            raise RuntimeError("M186 frozen numerical threshold mismatch")
        after_forbidden = [p.relative_to(candidate).as_posix() for p in candidate.rglob("*") if p.is_file() and ("__pycache__" in p.parts or p.suffix == ".pyc" or ".partial" in p.name)]
        if after_forbidden:
            raise RuntimeError(f"M186 gate polluted candidate: {after_forbidden[:4]}")
        result.update({
            "status": "PASS",
            "output_shape": raw["output_shape"],
            "metrics_vs_same_method_CPU_PS_golden": metrics,
            "vision_execution_device": "KV260 Cortex-A53 PS",
            "fpga_language_executed": False,
            "web_deployed": False,
            "next_gate": "Run fixed four-frame video-language E2E with the inherited M120 FPGA language/head path.",
        })
    except BaseException as error:
        result["error"] = f"{type(error).__name__}: {error}"
        result["fpga_language_executed"] = False
        result["web_deployed"] = False
        result["next_gate"] = "Repair and rerun only M186 PS vision; do not run FPGA video-language E2E."
    finally:
        result["total_ms"] = (time.monotonic() - started) * 1000.0
        atomic_json(args.result.resolve(), result)
    print("__M186_PS_VISION_RESULT_BEGIN__", flush=True)
    print(json.dumps(result, separators=(",", ":")), flush=True)
    print("__M186_PS_VISION_RESULT_END__", flush=True)
    print("M186_M181_PS_VISION_BOARD_PASS" if result["status"] == "PASS" else "M186_M181_PS_VISION_BOARD_FAIL", flush=True)
    return 0 if result["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
