#!/usr/bin/env python3
"""Screen natural BACT prompts with the exact M120+A8 software policy."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import sys
import time
from pathlib import Path

from PIL import Image


M120_MANIFEST_SHA256 = "5ff33d1922376e18277902a8b051d069315f79c11b4f63e8d72517acd1dcd5d0"
M120_BLOB_SHA256 = "9c7de8995a08602186c7090081bbfc10b7c51170ad7e544f2f2dc71333b4f21d"
M275_SHA256 = "234bba1a9b2796a2a231efd539427d39435715bda69a4f401b87f9273defb5bd"
M285_SHA256 = "ffc9cb62ba062a534ccc54f9d895ec2e3229c99fd4b0d65e37e10808d15f114a"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(16 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def atomic_json(path: Path, value: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    partial = path.with_suffix(path.suffix + f".partial-{os.getpid()}")
    partial.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    os.replace(partial, path)


def prepare(processor, views, prompt: str):
    images = [Image.fromarray(frame, mode="RGB") for frame in views]
    messages = [{
        "role": "user",
        "content": [{"type": "video"}, {"type": "text", "text": prompt}],
    }]
    rendered = processor.apply_chat_template(
        messages, tokenize=False, add_generation_prompt=True
    )
    return processor(text=[rendered], videos=[images], return_tensors="pt", padding=True)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--workspace", type=Path, required=True)
    parser.add_argument("--model", type=Path, required=True)
    parser.add_argument("--checkpoint", type=Path, required=True)
    parser.add_argument("--examples", type=Path, required=True)
    parser.add_argument("--result", type=Path, required=True)
    parser.add_argument("--threads", type=int, default=20)
    args = parser.parse_args()

    workspace = args.workspace.resolve()
    root = workspace / "deployment/mage_vl4b"
    m275_path = root / "M275_GPU_EXACT_PROMPT_SWEEP_RESULT.json"
    m285_path = root / "M285_M120_A8_BOUNDARY_DIAGNOSTIC_RESULT.json"
    if sha256(m275_path) != M275_SHA256 or sha256(m285_path) != M285_SHA256:
        raise RuntimeError("M286 predecessor identity mismatch")
    m275 = json.loads(m275_path.read_text(encoding="utf-8"))
    prompt_candidates = [
        {"name": item["name"], "prompt": item["prompt"]}
        for item in m275["candidates"]
    ]
    if len(prompt_candidates) != 4 or len({item["name"] for item in prompt_candidates}) != 4:
        raise RuntimeError("M286 expected four frozen natural prompt candidates")

    sys.path[:0] = [
        str(workspace / "scripts"),
        str(root / "scripts"),
        str(root / "m273_latest_binary_source"),
        str(root / "m246_knife_binary_source"),
    ]
    from m264_gpu_resolution_semantic_suite import build_samples
    from m273_latest_multiscale_contract import make_views
    from m246_knife_binary import KNIFE_NO_TOKEN_ID, KNIFE_YES_TOKEN_ID
    from mage_a8_runtime import install_packed_linear_a8_hooks
    from packed_checkpoint_artifact import load_packed_checkpoint

    import torch
    from transformers import AutoModelForCausalLM, AutoProcessor

    torch.set_num_threads(args.threads)
    checkpoint = args.checkpoint.resolve()
    manifest_path = checkpoint / "CHECKPOINT_MANIFEST.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if sha256(manifest_path) != M120_MANIFEST_SHA256:
        raise RuntimeError("M286 M120 manifest hash mismatch")
    if manifest.get("blob", {}).get("sha256") != M120_BLOB_SHA256:
        raise RuntimeError("M286 M120 blob declaration mismatch")

    result = {
        "date": "2026-09-02",
        "gate": "M286-M120-A8-natural-prompt-small-screen",
        "status": "FAIL",
        "classification": (
            "Exact M120 mixed-weight plus A8-G64 CPU screen over four frozen natural "
            "prompt candidates and four small labelled samples. It is a candidate-selection "
            "screen, not held-out accuracy, FPGA execution, timing, power, Web or real-time evidence."
        ),
        "m275_sha256": sha256(m275_path),
        "m285_sha256": sha256(m285_path),
    }
    started = time.perf_counter()
    handles = []
    try:
        processor = AutoProcessor.from_pretrained(
            args.model.resolve(), trust_remote_code=True, local_files_only=True
        )
        print("[M286] loading BF16 model shell on CPU", flush=True)
        model = AutoModelForCausalLM.from_pretrained(
            args.model.resolve(),
            trust_remote_code=True,
            local_files_only=True,
            torch_dtype=torch.bfloat16,
            low_cpu_mem_usage=True,
            attn_implementation="eager",
            device_map={"": "cpu"},
        ).eval()
        print("[M286] loading and verifying exact M120 checkpoint", flush=True)
        reload_info = load_packed_checkpoint(
            torch, model, checkpoint, verify_blob=True, row_chunk=32
        )
        if reload_info["manifest_sha256"] != M120_MANIFEST_SHA256:
            raise RuntimeError("M286 reloaded manifest mismatch")
        if reload_info["blob_sha256"] != M120_BLOB_SHA256:
            raise RuntimeError("M286 reloaded blob mismatch")
        handles, names = install_packed_linear_a8_hooks(
            torch, model, checkpoint, r"^(model\.language_model\.layers\.|lm_head$)"
        )
        if len(names) != 253:
            raise RuntimeError(f"M286 A8 hook closure mismatch {len(names)}")

        samples = build_samples(workspace, args.examples.resolve())
        if len(samples) != 4:
            raise RuntimeError(f"M286 expected four frozen samples, found {len(samples)}")
        sample_views = {
            sample.name: make_views(sample.frames_448[-1:]) for sample in samples
        }
        candidates = []
        for candidate in prompt_candidates:
            records = []
            token_count = None
            for sample in samples:
                inputs = prepare(processor, sample_views[sample.name], candidate["prompt"])
                observed_tokens = int(inputs["input_ids"].shape[1])
                token_count = observed_tokens if token_count is None else token_count
                if observed_tokens != token_count:
                    raise RuntimeError("M286 prompt geometry changed between samples")
                probe_started = time.perf_counter()
                with torch.inference_mode():
                    output = model(**inputs, use_cache=False)
                logits = output.logits[0, -1].to(dtype=torch.float32, device="cpu").contiguous()
                finite = bool(torch.isfinite(logits).all().item())
                no_logit = float(logits[KNIFE_NO_TOKEN_ID].item())
                yes_logit = float(logits[KNIFE_YES_TOKEN_ID].item())
                decision = 1 if yes_logit >= no_logit else 0
                expected = 1 if sample.expected.knife == "有" else 0
                records.append({
                    "name": sample.name,
                    "expected": expected,
                    "decision": decision,
                    "pass": finite and decision == expected,
                    "finite": finite,
                    "no_logit": no_logit,
                    "yes_logit": yes_logit,
                    "margin_yes_minus_no": yes_logit - no_logit,
                    "absolute_decision_margin": abs(yes_logit - no_logit),
                    "forward_ms": (time.perf_counter() - probe_started) * 1000.0,
                })
            batches = math.ceil(int(token_count) / 32)
            candidates.append({
                "name": candidate["name"],
                "prompt": candidate["prompt"],
                "prompt_tokens": int(token_count),
                "t32_batches": batches,
                "expected_logical_fpga_calls": 154 * batches + 8,
                "records": records,
                "suite_pass": all(item["pass"] for item in records),
                "all_finite": all(item["finite"] for item in records),
                "minimum_absolute_margin": min(
                    item["absolute_decision_margin"] for item in records
                ),
            })

        passing = [item for item in candidates if item["suite_pass"]]
        selected = None
        if passing:
            minimum_batches = min(item["t32_batches"] for item in passing)
            same_batch = [item for item in passing if item["t32_batches"] == minimum_batches]
            selected = max(
                same_batch,
                key=lambda item: (
                    item["minimum_absolute_margin"],
                    item["prompt_tokens"],
                    item["name"],
                ),
            )
        screen_pass = selected is not None
        result.update({
            "status": "PASS_SMALL_SCREEN" if screen_pass else "FAIL_SMALL_SCREEN",
            "model": "microsoft/Mage-VL",
            "backend": "WSL CPU exact reconstructed M120 weights plus A8-G64 hooks",
            "checkpoint": reload_info,
            "a8_hook_count": len(names),
            "sample_count": len(samples),
            "candidates": candidates,
            "selected_for_target_scene_validation": (
                None if selected is None else {
                    key: selected[key]
                    for key in (
                        "name", "prompt", "prompt_tokens", "t32_batches",
                        "expected_logical_fpga_calls", "minimum_absolute_margin"
                    )
                }
            ),
            "selection_rule": (
                "Require all four decisions and finiteness; minimize T32 batches; within "
                "that batch count maximize the minimum M120+A8 binary margin; then retain "
                "the larger natural prompt-token budget."
            ),
            "semantic_accuracy_passed": False,
            "threshold_calibrated": False,
            "board_execution_run": False,
            "active_board_service_changed": False,
            "boot_dtb_cma_partitions_changed": False,
            "stable_rollback_preserved": True,
            "next_gate": (
                "Freeze the selected natural candidate only as a target-scene-validation "
                "candidate. Build a labelled held-out monitoring manifest and compare all "
                "four BACT baselines before any board promotion."
            ),
        })
    except BaseException as exc:
        result["error"] = f"{type(exc).__name__}: {exc}"
        result["next_gate"] = "Fix and rerun this same offline screen; do not touch the board."
    finally:
        for handle in reversed(handles):
            handle.remove()
        result["wall_ms"] = (time.perf_counter() - started) * 1000.0
        result["source_sha256"] = sha256(Path(__file__).resolve())
        atomic_json(args.result, result)
        print(json.dumps(result, ensure_ascii=False), flush=True)

    print("M286_M120_A8_NATURAL_PROMPT_SCREEN_PASS" if result["status"] == "PASS_SMALL_SCREEN" else "M286_M120_A8_NATURAL_PROMPT_SCREEN_FAIL", flush=True)
    return 0 if result["status"] == "PASS_SMALL_SCREEN" else 1


if __name__ == "__main__":
    raise SystemExit(main())
