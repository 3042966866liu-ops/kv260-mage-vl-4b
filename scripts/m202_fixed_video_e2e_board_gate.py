#!/usr/bin/env python3
"""Fixed four-frame Mage-VL E2E gate: PS vision plus M120 FPGA language/head."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import platform
import sys
import time
from pathlib import Path
from types import SimpleNamespace

import numpy as np


sys.dont_write_bytecode = True
ROOT = Path("/home/ubuntu/tellme_m120_m89x2_20260901")
VIDEO = ROOT / "m181_m120_video_board_candidate"
TEXT = ROOT / "m175_m120_fixed_text_candidate"
WEIGHTS = ROOT / "m120_fulltext_weights_0x4D395832"
VIDEO_MANIFEST_SHA = "1596536bfe6865cb7eab5c038d8b4da8b666afc7cbd629ddc4559781727151d6"
TEXT_MANIFEST_SHA = "406dcca340e4604baeb761445795391c43ec26bd99fa06ffae893d597b17414f"
M198_SHA = "b05671184eddb853c30091f3f0cb4718f5a96be9080dee210387bd483cce3209"
BUILD_ID = "0x4D395832"
EXPECTED_PROMPT_TOKENS = 849
EXPECTED_CALLS = 4166


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(16 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def atomic_json(path: Path, value: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + f".partial-{os.getpid()}")
    temporary.write_text(json.dumps(value, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    os.replace(temporary, path)


def fixed_frames() -> np.ndarray:
    """Deterministic decoded RGB frames with spatial, temporal and color motion."""
    y, x = np.indices((448, 448), dtype=np.uint16)
    frames = []
    for index in range(4):
        red = (x + 29 * index) & 255
        green = (y + 47 * index) & 255
        blue = ((x // 2 + y // 3 + 61 * index) & 255)
        frames.append(np.stack((red, green, blue), axis=-1).astype(np.uint8))
    return np.stack(frames, axis=0)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--gate-root", type=Path, required=True)
    parser.add_argument("--board-gate", type=Path, required=True)
    parser.add_argument("--m198-result", type=Path, required=True)
    parser.add_argument("--environment-result", type=Path, required=True)
    parser.add_argument("--result", type=Path, required=True)
    args = parser.parse_args()
    started = time.monotonic()
    result: dict[str, object] = {
        "date": "2026-09-01",
        "gate": "M202-M200-fixed-four-frame-video-language-E2E",
        "status": "FAIL",
        "classification": "Real-KV260 fixed decoded-four-frame PS-vision plus FPGA language/head E2E; not arbitrary video, Web or accepted performance evidence.",
        "candidate_build_id": BUILD_ID,
        "fixed_prompt": "Describe the motion and color change in this short video in one sentence.",
        "max_new_tokens": 1,
        "video_package_manifest_sha256": VIDEO_MANIFEST_SHA,
        "text_package_manifest_sha256": TEXT_MANIFEST_SHA,
        "m198_formal_result_sha256": M198_SHA,
        "boot_dtb_cma_partitions_services_changed": False,
        "stable_rollback_preserved": True,
        "web_deployed": False,
    }
    runtime = None
    try:
        gate_root = args.gate_root.resolve()
        if platform.machine().lower() not in {"aarch64", "arm64"}:
            raise RuntimeError(f"M202 requires aarch64, observed={platform.machine()}")
        if sha256(VIDEO / "PACKAGE_MANIFEST.json") != VIDEO_MANIFEST_SHA:
            raise RuntimeError("M202 video package identity mismatch")
        if sha256(TEXT / "PACKAGE_MANIFEST.json") != TEXT_MANIFEST_SHA:
            raise RuntimeError("M202 text package identity mismatch")
        if sha256(args.m198_result) != M198_SHA:
            raise RuntimeError("M202 exact M198 predecessor hash mismatch")
        m198 = json.loads(args.m198_result.read_text(encoding="utf-8"))
        if (m198.get("status") != "PASS" or
                m198.get("fp32_encoder_layers") != list(range(6, 24))):
            raise RuntimeError("M202 M198 predecessor is not accepted")
        environment = json.loads(args.environment_result.read_text(encoding="utf-8"))
        if (environment.get("status") != "PASS" or
                environment.get("package_manifest_sha256") != TEXT_MANIFEST_SHA or
                environment.get("xcl_probe_count") != 1 or
                environment.get("pynq_device_count") != 1):
            raise RuntimeError("M202 same-terminal FPGA environment preflight is not PASS")
        sys.path.insert(0, str(gate_root))
        sys.path.insert(1, str(VIDEO))
        from video_server import M120VideoRuntime, make_config

        config = make_config(VIDEO, TEXT, WEIGHTS, args.board_gate.resolve())
        runtime = M120VideoRuntime(config)
        request = SimpleNamespace(
            prompt=result["fixed_prompt"], max_new_tokens=1, frames_rgb_u8=fixed_frames()
        )
        events = []
        for name, payload in runtime.stream(request):
            events.append({"event": name, "payload": payload})
            if name in {"stage", "token", "complete"}:
                print(f"M202_EVENT {name} {json.dumps(payload, ensure_ascii=False, separators=(',', ':'))}", flush=True)
        complete = [entry["payload"] for entry in events if entry["event"] == "complete"]
        tokens = [entry["payload"] for entry in events if entry["event"] == "token"]
        if len(complete) != 1 or len(tokens) != 1:
            raise RuntimeError(f"M202 event cardinality mismatch complete={len(complete)} token={len(tokens)}")
        proof = complete[0].get("proof", {})
        if (complete[0].get("status") != "PASS" or
                complete[0].get("prompt_tokens") != EXPECTED_PROMPT_TOKENS or
                complete[0].get("generated_tokens") != 1 or
                str(proof.get("build_id", "")).lower() != BUILD_ID.lower() or
                proof.get("pl_logical_chain_calls") != EXPECTED_CALLS or
                proof.get("expected_pl_logical_chain_calls") != EXPECTED_CALLS or
                int(proof.get("pl_expected_macros", 0)) <= 0 or
                proof.get("language_cpu_linear_fallback") is not False):
            raise RuntimeError("M202 fixed video FPGA proof mismatch")
        result.update({
            "status": "PASS",
            "prompt_tokens": complete[0]["prompt_tokens"],
            "generated_tokens": 1,
            "generated_token_id": tokens[0]["token_id"],
            "generated_text": tokens[0]["text"],
            "first_token_ms": complete[0]["first_token_ms"],
            "stream_total_ms": complete[0]["total_ms"],
            "fpga_proof": proof,
            "vision_compute_policy": "layers 0-5 BF16; layers 6-23 FP32; each FP32 block returns BF16 state",
            "input_contract": "4 deterministic decoded RGB frames, each 448x448x3 uint8",
            "next_gate": "Run the same fixed request through the board HTTP/SSE endpoint, then unlock arbitrary browser video only after that PASS.",
        })
    except BaseException as error:
        result["error"] = f"{type(error).__name__}: {error}"
        result["next_gate"] = "Debug and rerun only M202 fixed video-language E2E."
    finally:
        if runtime is not None:
            runtime.close()
        result["wall_ms"] = (time.monotonic() - started) * 1000.0
        atomic_json(args.result.resolve(), result)
    print("__M202_FIXED_VIDEO_E2E_RESULT_BEGIN__", flush=True)
    print(json.dumps(result, ensure_ascii=False, separators=(",", ":")), flush=True)
    print("__M202_FIXED_VIDEO_E2E_RESULT_END__", flush=True)
    print("M202_FIXED_VIDEO_E2E_PASS" if result["status"] == "PASS" else "M202_FIXED_VIDEO_E2E_FAIL", flush=True)
    return 0 if result["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
