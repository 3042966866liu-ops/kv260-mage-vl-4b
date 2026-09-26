#!/usr/bin/env python3
"""One isolated real-KV260 M276 functional, stage and first-token gate."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import resource
import time
from pathlib import Path
from types import SimpleNamespace

import numpy as np

import m276_video_runtime
import video_server
from m276_prompt_contract import M276_KNIFE_PROMPT


EXPECTED_BUILD = "0x4d395832"
EXPECTED_CALLS = 778
EXPECTED_PROMPT_TOKENS = 159
EXPECTED_VISUAL_TOKENS = 98
EXPECTED_SELECTED = [3]
EXPECTED_M244_SHA256 = "b134fc00f7e2be60d9444f0e81203561972455d78907cdb6515462a98243e392"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(4 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def atomic_json(path: Path, value: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    partial = path.with_name(path.name + f".partial-{os.getpid()}")
    partial.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    os.replace(partial, path)


def load_frames(root: Path) -> np.ndarray:
    names = (
        "frame_00_0068_rgb448.npy",
        "frame_01_0102_rgb448.npy",
        "frame_02_0137_rgb448.npy",
        "frame_03_0171_rgb448.npy",
    )
    frames = np.stack([np.load(root / name, allow_pickle=False) for name in names])
    if frames.shape != (4, 448, 448, 3) or frames.dtype != np.uint8:
        raise RuntimeError(f"M277 fixture geometry mismatch {frames.shape}/{frames.dtype}")
    return np.ascontiguousarray(frames)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--candidate", type=Path, required=True)
    parser.add_argument("--text-candidate", type=Path, required=True)
    parser.add_argument("--weights-root", type=Path, required=True)
    parser.add_argument("--board-gate", type=Path, required=True)
    parser.add_argument("--fixture-root", type=Path, required=True)
    parser.add_argument("--m244-baseline", type=Path, required=True)
    parser.add_argument("--package-manifest-sha256", required=True)
    parser.add_argument("--result", type=Path, required=True)
    args = parser.parse_args()
    process_started = time.perf_counter()
    events: list[dict] = []
    stage_marks: dict[str, float] = {}
    runtime = None
    error = None
    decoder_evidence = None
    frames_sha256 = None
    try:
        if sha256(args.m244_baseline) != EXPECTED_M244_SHA256:
            raise RuntimeError("M277 M244 baseline hash mismatch")
        baseline_ms = float(json.loads(args.m244_baseline.read_text(encoding="utf-8"))["elapsed_ms"])
        frames = load_frames(args.fixture_root)
        frames_sha256 = hashlib.sha256(frames.tobytes()).hexdigest()
        config = video_server.make_config(
            args.candidate.resolve(),
            args.text_candidate.resolve(),
            args.weights_root.resolve(),
            args.board_gate.resolve(),
        )
        runtime = m276_video_runtime.M276ShortPromptBinaryRuntime(config)
        request = SimpleNamespace(prompt=M276_KNIFE_PROMPT, max_new_tokens=1, frames_rgb_u8=frames)
        for name, payload in runtime.stream(request):
            elapsed_ms = (time.perf_counter() - process_started) * 1000.0
            item = {"event": name, "elapsed_ms": elapsed_ms, "payload": payload}
            events.append(item)
            if name == "stage" and isinstance(payload, dict) and payload.get("name") in {"preprocess", "vision", "prefill"}:
                stage_name = str(payload["name"])
                if stage_name in stage_marks:
                    raise RuntimeError(f"M277 duplicate stage event {stage_name}")
                stage_marks[stage_name] = elapsed_ms
            print("M277_EVENT " + json.dumps(item, ensure_ascii=False, separators=(",", ":")), flush=True)
        if runtime.vision is not None and hasattr(runtime.vision, "decoder_evidence"):
            decoder_evidence = runtime.vision.decoder_evidence()
    except BaseException as exc:
        error = f"{type(exc).__name__}: {exc}"
    finally:
        if runtime is not None:
            try:
                runtime.close()
            except BaseException as close_exc:
                if error is None:
                    error = f"close {type(close_exc).__name__}: {close_exc}"

    complete = [item["payload"] for item in events if item["event"] == "complete"]
    token = [item["payload"] for item in events if item["event"] == "token"]
    observation = [item["payload"] for item in events if item["event"] == "knife_observation"]
    final = complete[0] if len(complete) == 1 else {}
    proof = final.get("proof", {}) if isinstance(final, dict) else {}
    baseline_ms = float(locals().get("baseline_ms", 1069764.9999999995))
    ttft_ms = final.get("first_token_ms")
    total_ms = final.get("total_ms")
    token_mark = next((float(item["elapsed_ms"]) for item in events if item["event"] == "token"), None)
    complete_mark = next((float(item["elapsed_ms"]) for item in events if item["event"] == "complete"), None)

    def delta(first: str, second: str):
        values = {**stage_marks, "token": token_mark, "complete": complete_mark}
        if values.get(first) is None or values.get(second) is None:
            return None
        return float(values[second]) - float(values[first])

    stage_timing_ms = {
        "process_start_and_runtime_load_to_preprocess": stage_marks.get("preprocess"),
        "preprocess": delta("preprocess", "vision"),
        "vision": delta("vision", "prefill"),
        "language_prefill_to_first_token": delta("prefill", "token"),
        "token_to_complete": delta("token", "complete"),
    }
    functional_pass = bool(
        error is None
        and len(complete) == len(token) == len(observation) == 1
        and set(stage_marks) == {"preprocess", "vision", "prefill"}
        and final.get("status") == "PASS"
        and final.get("prompt_tokens") == EXPECTED_PROMPT_TOKENS
        and final.get("decode_calls") == 0
        and final.get("selected_frame_indices") == EXPECTED_SELECTED
        and token[0].get("text") == "0"
        and token[0].get("token_id") == 15
        and token[0].get("knife_verdict") == "ABSENT"
        and observation[0].get("verdict") == "ABSENT"
        and str(proof.get("build_id", "")).lower() == EXPECTED_BUILD
        and proof.get("pl_logical_chain_calls") == EXPECTED_CALLS
        and proof.get("expected_pl_logical_chain_calls") == EXPECTED_CALLS
        and int(proof.get("pl_expected_macros", 0)) > 0
        and proof.get("language_cpu_linear_fallback") is False
        and proof.get("decode_calls") == 0
        and decoder_evidence is not None
        and decoder_evidence.get("cache_entries") == 26
        and decoder_evidence.get("cache_bytes") == 66699264
        and decoder_evidence.get("cache_misses") == 26
    )
    faster = bool(functional_pass and total_ms is not None and float(total_ms) < baseline_ms)
    target_5s = bool(functional_pass and ttft_ms is not None and float(ttft_ms) <= 5000.0)
    status = "PASS_FUNCTIONAL_FASTER_THAN_M244" if functional_pass and faster else "FAIL_FUNCTIONAL_OR_SPEED"
    result = {
        "date": "2026-09-02",
        "gate": "M277-M276-real-KV260-fixed-window-binary-TTFT",
        "status": status,
        "functional_status": "PASS" if functional_pass else "FAIL",
        "improvement_status": "PASS" if faster else "FAIL",
        "target_5s_status": "PASS" if target_5s else "FAIL",
        "classification": "Real KV260 isolated M276 latest-alarm global/detail 98-token vision plus 159-token M238/M241 T32 constrained 0/1 first-token gate; calibrated accuracy and Web promotion remain separate.",
        "package_manifest_sha256": args.package_manifest_sha256,
        "frames_sha256": frames_sha256,
        "visual_tokens": EXPECTED_VISUAL_TOKENS,
        "prompt_tokens": final.get("prompt_tokens"),
        "selected_frame_indices": final.get("selected_frame_indices"),
        "first_token_ms": ttft_ms,
        "total_ms": total_ms,
        "m244_elapsed_baseline_ms": baseline_ms,
        "total_reduction_vs_m244_percent": None if total_ms is None else (1.0 - float(total_ms) / baseline_ms) * 100.0,
        "stage_event_elapsed_ms": stage_marks,
        "stage_timing_ms": stage_timing_ms,
        "target_5s_ms": 5000.0,
        "events": events,
        "decoder_evidence": decoder_evidence,
        "error": error,
        "process_max_rss_kib": int(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss),
        "candidate_service_retained": False,
        "active_service_restoration_required": True,
        "boot_dtb_cma_partitions_changed": False,
        "stable_rollback_preserved": True,
        "next_gate": "Use measured stage timing to optimize the dominant stage; only a later PASS may unlock Web integration.",
    }
    atomic_json(args.result, result)
    print("__M277_BOARD_RESULT_BEGIN__", flush=True)
    print(json.dumps(result, ensure_ascii=False, separators=(",", ":")), flush=True)
    print("__M277_BOARD_RESULT_END__", flush=True)
    print("M277_FIXED_WINDOW_PASS" if status.startswith("PASS") else "M277_FIXED_WINDOW_FAIL", flush=True)
    return 0 if status.startswith("PASS") else 1


if __name__ == "__main__":
    raise SystemExit(main())

