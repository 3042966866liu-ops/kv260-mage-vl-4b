#!/usr/bin/env python3
"""Bounded two-window continuous-video reuse gate on the real KV260."""

from __future__ import annotations

import argparse
import gc
import hashlib
import json
import os
import platform
import sys
import time
from collections import deque
from pathlib import Path
from types import SimpleNamespace

import numpy as np


ROOT = Path("/home/ubuntu/tellme_m120_m89x2_20260901")
VIDEO = ROOT / "m181_m120_video_board_candidate"
TEXT = ROOT / "m175_m120_fixed_text_candidate"
WEIGHTS = ROOT / "m120_fulltext_weights_0x4D395832"
M202_SHA = "47fa5da23cde794994062979f113c4cdea224614c1277976c66d85dd3f259d98"
TEXT_SHA = "406dcca340e4604baeb761445795391c43ec26bd99fa06ffae893d597b17414f"
BUILD_ID = "0x4D395832"
PROMPT = "Describe the motion and color change in this short video in one sentence."


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(8 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def atomic_json(path: Path, value: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + f".partial-{os.getpid()}")
    temporary.write_text(json.dumps(value, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    os.replace(temporary, path)


def frame(index: int) -> np.ndarray:
    y, x = np.indices((448, 448), dtype=np.uint16)
    return np.stack(((x + 29 * index) & 255, (y + 47 * index) & 255,
                     (x // 2 + y // 3 + 61 * index) & 255), axis=-1).astype(np.uint8)


class SlidingWindow:
    def __init__(self, size: int = 4, stride: int = 2):
        if not 1 <= stride <= size:
            raise ValueError("invalid sliding-window geometry")
        self.size, self.stride = size, stride
        self.frames: deque[np.ndarray] = deque()

    def push(self, value: np.ndarray) -> np.ndarray | None:
        item = np.asarray(value)
        if item.shape != (448, 448, 3) or item.dtype != np.uint8:
            raise ValueError("continuous frame contract mismatch")
        self.frames.append(np.ascontiguousarray(item))
        if len(self.frames) < self.size:
            return None
        output = np.stack(tuple(self.frames), axis=0)
        for _ in range(self.stride):
            self.frames.popleft()
        return output


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--gate-root", type=Path, required=True)
    parser.add_argument("--board-gate", type=Path, required=True)
    parser.add_argument("--m202-result", type=Path, required=True)
    parser.add_argument("--environment-result", type=Path, required=True)
    parser.add_argument("--result", type=Path, required=True)
    args = parser.parse_args()
    started = time.monotonic()
    result: dict[str, object] = {
        "date": "2026-09-01", "gate": "M204-bounded-continuous-video-two-window-reuse",
        "status": "FAIL",
        "classification": "Real-KV260 bounded six-frame/two-overlapping-window continuous-input reuse gate; not live camera, real-time, HTTP/SSE or public Web evidence.",
        "candidate_build_id": BUILD_ID, "window_size": 4, "window_stride": 2,
        "input_frame_count": 6, "expected_window_count": 2,
        "boot_dtb_cma_partitions_services_changed": False, "stable_rollback_preserved": True,
        "web_deployed": False,
    }
    runtime = None
    try:
        if platform.machine().lower() not in {"aarch64", "arm64"}:
            raise RuntimeError("M204 requires aarch64")
        if sha256(args.m202_result) != M202_SHA:
            raise RuntimeError("M204 exact M202 predecessor hash mismatch")
        predecessor = json.loads(args.m202_result.read_text(encoding="utf-8"))
        if predecessor.get("status") != "PASS" or predecessor.get("fpga_proof", {}).get("pl_logical_chain_calls") != 4166:
            raise RuntimeError("M204 M202 predecessor is not accepted")
        environment = json.loads(args.environment_result.read_text(encoding="utf-8"))
        if environment.get("status") != "PASS" or environment.get("package_manifest_sha256") != TEXT_SHA:
            raise RuntimeError("M204 environment preflight mismatch")
        sys.path.insert(0, str(args.gate_root.resolve()))
        sys.path.insert(1, str(VIDEO))
        from video_server import M120VideoRuntime, make_config

        runtime = M120VideoRuntime(make_config(VIDEO, TEXT, WEIGHTS, args.board_gate.resolve()))
        load_started = time.monotonic()
        runtime.load()
        load_ms = (time.monotonic() - load_started) * 1000.0
        identities = (id(runtime.board), id(runtime.vision), id(runtime.language), id(runtime.tokenizer))
        before_all = runtime.board.evidence()
        sliding = SlidingWindow()
        windows = []
        for index in range(6):
            ready = sliding.push(frame(index))
            if ready is not None:
                windows.append(ready)
        if len(windows) != 2 or not np.array_equal(windows[0][2:], windows[1][:2]):
            raise RuntimeError("M204 sliding-window overlap mismatch")
        measurements = []
        for index, frames in enumerate(windows):
            print(f"M204_WINDOW_{index}_BEGIN", flush=True)
            events = list(runtime.stream(SimpleNamespace(prompt=PROMPT, max_new_tokens=1, frames_rgb_u8=frames)))
            complete = [payload for name, payload in events if name == "complete"]
            tokens = [payload for name, payload in events if name == "token"]
            if len(complete) != 1 or len(tokens) != 1:
                raise RuntimeError(f"M204 window {index} event cardinality mismatch")
            proof = complete[0].get("proof", {})
            if (complete[0].get("prompt_tokens") != 849 or complete[0].get("generated_tokens") != 1 or
                    proof.get("pl_logical_chain_calls") != 4166 or
                    proof.get("expected_pl_logical_chain_calls") != 4166 or
                    str(proof.get("build_id", "")).lower() != BUILD_ID.lower() or
                    proof.get("language_cpu_linear_fallback") is not False):
                raise RuntimeError(f"M204 window {index} FPGA proof mismatch")
            measurements.append({
                "window_index": index, "source_frame_indices": [0, 1, 2, 3] if index == 0 else [2, 3, 4, 5],
                "generated_token_id": tokens[0]["token_id"], "generated_text": tokens[0]["text"],
                "first_token_ms": complete[0]["first_token_ms"], "total_ms": complete[0]["total_ms"],
                "fpga_proof": proof,
            })
            print(f"M204_WINDOW_{index}_PASS token={tokens[0]['token_id']} calls=4166", flush=True)
            del events, complete, tokens, frames
            gc.collect()
        after_all = runtime.board.evidence()
        total_calls = int(after_all["logical_calls"]) - int(before_all["logical_calls"])
        total_macros = int(after_all["logical_expected_macros"]) - int(before_all["logical_expected_macros"])
        identity_after = (id(runtime.board), id(runtime.vision), id(runtime.language), id(runtime.tokenizer))
        if total_calls != 8332 or total_macros <= 0 or identity_after != identities:
            raise RuntimeError(f"M204 cross-window reuse proof mismatch calls={total_calls}")
        result.update({
            "status": "PASS", "runtime_load_count": 1, "runtime_load_ms": load_ms,
            "runtime_identity_reused": True, "overlap_frame_count": 2,
            "processed_window_count": 2, "windows": measurements,
            "total_pl_logical_chain_calls": total_calls, "expected_total_pl_logical_chain_calls": 8332,
            "total_pl_expected_macros": total_macros,
            "backpressure_policy": "single inference worker; bounded newest-six-frame source; no unbounded request queue",
            "next_gate": "Expose this bounded sliding-window controller through a local HTTP/SSE endpoint and verify two streamed windows before public tunneling.",
        })
    except BaseException as error:
        result["error"] = f"{type(error).__name__}: {error}"
        result["next_gate"] = "Debug and rerun only M204 bounded continuous-video gate."
    finally:
        if runtime is not None:
            runtime.close()
        result["wall_ms"] = (time.monotonic() - started) * 1000.0
        atomic_json(args.result.resolve(), result)
    print("__M204_CONTINUOUS_VIDEO_RESULT_BEGIN__", flush=True)
    print(json.dumps(result, ensure_ascii=False, separators=(",", ":")), flush=True)
    print("__M204_CONTINUOUS_VIDEO_RESULT_END__", flush=True)
    print("M204_CONTINUOUS_VIDEO_PASS" if result["status"] == "PASS" else "M204_CONTINUOUS_VIDEO_FAIL", flush=True)
    return 0 if result["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
