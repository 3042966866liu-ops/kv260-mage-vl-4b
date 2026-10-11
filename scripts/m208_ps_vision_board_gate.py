#!/usr/bin/env python3
"""Real-KV260 fixed-four-frame gate for the M207 FP32-GEMM candidate."""

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
from collections import deque
from pathlib import Path


PACKAGE_SHA = "1596536bfe6865cb7eab5c038d8b4da8b666afc7cbd629ddc4559781727151d6"
M198_SHA = "b05671184eddb853c30091f3f0cb4718f5a96be9080dee210387bd483cce3209"
M207_SHA = "6f2b84b306c8f320ba3fbdc00a6acb4b4d06b64bbda483e32ce7fcf490c7c313"
BASELINE_FORWARD_MS = 1072673.0626030038
ROOT = Path("/home/ubuntu/tellme_m120_m89x2_20260901")
CANDIDATE = ROOT / "m181_m120_video_board_candidate"
SITE_PACKAGES = ROOT / "m190_mage_runtime"
RAW_RESULT = ROOT / "results/M208_M207_PS_VISION_RAW_RESULT.json"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(8 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def atomic_json(path: Path, value: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + f".partial-{os.getpid()}")
    temporary.write_text(json.dumps(value, indent=2) + "\n", encoding="utf-8")
    os.replace(temporary, path)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--gate-root", type=Path, required=True)
    parser.add_argument("--candidate", type=Path, required=True)
    parser.add_argument("--m198-result", type=Path, required=True)
    parser.add_argument("--m207-offline-result", type=Path, required=True)
    parser.add_argument("--environment-result", type=Path, required=True)
    parser.add_argument("--result", type=Path, required=True)
    args = parser.parse_args()
    started = time.monotonic()
    result = {
        "date": "2026-09-01",
        "gate": "M208-M207-fixed-four-frame-PS-vision-FP32-W4-GEMM",
        "status": "FAIL",
        "classification": (
            "Real-KV260 fixed-four-frame PS-vision numerical/performance gate; "
            "not complete video-language, continuous stream or Web evidence."
        ),
        "candidate_build_id": "0x4D395832",
        "compute_policy": (
            "all W4 Linear GEMMs use FP32; operands for BF16 blocks are first rounded "
            "to BF16 then promoted; M198 L0-5 BF16/L6-23 FP32/BF16-boundary topology retained"
        ),
        "thresholds": {
            "cosine_minimum": 0.999,
            "rmse_maximum": 0.05,
            "bf16_gemm_warning_count_maximum": 0,
            "vision_forward_ms_maximum_exclusive": BASELINE_FORWARD_MS,
        },
        "boot_dtb_cma_partitions_services_changed": False,
        "stable_rollback_preserved": True,
        "web_deployed": False,
    }
    try:
        gate_root = args.gate_root.resolve()
        if args.candidate.resolve() != CANDIDATE or args.result.resolve().parent != ROOT / "results":
            raise RuntimeError("M208 fixed path identity mismatch")
        if platform.machine().lower() not in {"aarch64", "arm64"}:
            raise RuntimeError(f"M208 requires aarch64, observed={platform.machine()}")
        if sha256(args.m198_result) != M198_SHA:
            raise RuntimeError("M208 exact M198 predecessor hash mismatch")
        m198 = json.loads(args.m198_result.read_text(encoding="utf-8"))
        if m198.get("status") != "PASS":
            raise RuntimeError("M208 M198 predecessor is not PASS")
        if sha256(args.m207_offline_result) != M207_SHA:
            raise RuntimeError("M208 exact M207 offline result hash mismatch")
        offline = json.loads(args.m207_offline_result.read_text(encoding="utf-8"))
        if (offline.get("status") != "PASS"
                or offline.get("bf16_gemm_warning_count") != 0
                or offline.get("fp32_encoder_layers") != list(range(6, 24))):
            raise RuntimeError("M208 M207 offline policy is not accepted")
        environment = json.loads(args.environment_result.read_text(encoding="utf-8"))
        if environment.get("status") != "PASS" or environment.get("package_manifest_sha256") != "406dcca340e4604baeb761445795391c43ec26bd99fa06ffae893d597b17414f":
            raise RuntimeError("M208 environment preflight mismatch")
        candidate_manifest = args.candidate / "PACKAGE_MANIFEST.json"
        if sha256(candidate_manifest) != PACKAGE_SHA:
            raise RuntimeError("M208 candidate package manifest mismatch")
        required = (
            "ps_vision_runtime.py", "m206_ps_vision_runtime.py",
            "m207_ps_vision_runtime.py", "m207_test_ps_vision_runtime.py",
        )
        if any(not (gate_root / name).is_file() for name in required):
            raise RuntimeError("M208 runtime source closure missing")
        if RAW_RESULT.exists():
            raise RuntimeError("M208 requires absent raw result")
        env = os.environ.copy()
        env.update({
            "PYTHONPATH": f"{gate_root}:{SITE_PACKAGES}",
            "PYTHONDONTWRITEBYTECODE": "1",
            "TRANSFORMERS_OFFLINE": "1",
            "HF_HUB_OFFLINE": "1",
        })
        command = [
            sys.executable, str(gate_root / "m207_test_ps_vision_runtime.py"),
            "--model-code", str(CANDIDATE / "ps_vision_payload"),
            "--layout", str(CANDIDATE / "vision_layout"),
            "--raw-manifest", str(CANDIDATE / "auxiliary/M90_VISION_RAW_AUX_MANIFEST.json"),
            "--processor-fixture", str(CANDIDATE / "fixtures/official_four_frame_processor.npz"),
            "--golden", str(CANDIDATE / "fixtures/m56_w4_vision_merged_cpu_bf16.npz"),
            "--result", str(RAW_RESULT),
            "--heartbeat-seconds", "30",
        ]
        output_tail: deque[str] = deque(maxlen=1200)
        vision_started = time.monotonic()
        process = subprocess.Popen(
            command, cwd=gate_root, env=env, text=True,
            stdout=subprocess.PIPE, stderr=subprocess.STDOUT, bufsize=1,
        )
        assert process.stdout is not None
        for line in process.stdout:
            print(line, end="", flush=True)
            output_tail.append(line)
            if time.monotonic() - vision_started > 5400:
                process.kill()
                raise TimeoutError("M208 vision subprocess timeout")
        exit_code = process.wait()
        result["vision_wall_ms"] = (time.monotonic() - vision_started) * 1000.0
        result["test_exit_code"] = exit_code
        result["test_output_tail"] = "".join(output_tail)[-24000:]
        if not RAW_RESULT.is_file():
            raise RuntimeError("M208 raw numerical result missing")
        raw = json.loads(RAW_RESULT.read_text(encoding="utf-8"))
        result["raw_result"] = raw
        metrics = raw.get("metrics_vs_M56_W4_BF16_golden", {})
        cosine = float(metrics.get("cosine_similarity", float("nan")))
        rmse = float(metrics.get("rmse", float("nan")))
        forward_ms = float(raw.get("vision_forward_ms", float("inf")))
        if (exit_code != 0 or raw.get("status") != "PASS"
                or raw.get("finite") is not True
                or not math.isfinite(cosine) or cosine < 0.999
                or not math.isfinite(rmse) or rmse > 0.05
                or raw.get("bf16_gemm_warning_count") != 0
                or not math.isfinite(forward_ms) or forward_ms >= BASELINE_FORWARD_MS):
            raise RuntimeError("M208 numerical/performance acceptance failed")
        result.update({
            "status": "PASS",
            "output_shape": raw.get("output_shape"),
            "metrics_vs_same_method_CPU_PS_golden": metrics,
            "vision_forward_ms": forward_ms,
            "process_max_rss_kib": raw.get("process_max_rss_kib"),
            "bf16_gemm_warning_count": 0,
            "speedup_vs_m198_forward": BASELINE_FORWARD_MS / forward_ms,
            "fpga_language_executed": False,
            "next_gate": (
                "Rebase fixed video-language E2E on M207, then implement a bounded "
                "latest-only continuous source rather than finite queued windows."
            ),
        })
    except BaseException as error:
        result["error"] = f"{type(error).__name__}: {error}"
        result["fpga_language_executed"] = False
        result["next_gate"] = "Debug and rerun only M208 fixed-four-frame PS vision."
    finally:
        result["total_ms"] = (time.monotonic() - started) * 1000.0
        atomic_json(args.result.resolve(), result)
    print("__M208_PS_VISION_RESULT_BEGIN__", flush=True)
    print(json.dumps(result, ensure_ascii=False, separators=(",", ":")), flush=True)
    print("__M208_PS_VISION_RESULT_END__", flush=True)
    print("M208_M207_PS_VISION_BOARD_PASS" if result["status"] == "PASS" else "M208_M207_PS_VISION_BOARD_FAIL", flush=True)
    return 0 if result["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())

