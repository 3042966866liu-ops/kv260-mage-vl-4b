#!/usr/bin/env python3
"""One-model-load M120+A8 screen for the four frozen BACT baselines."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
from pathlib import Path
import sys
import time

from PIL import Image


M120_MANIFEST_SHA256 = "5ff33d1922376e18277902a8b051d069315f79c11b4f63e8d72517acd1dcd5d0"
M120_BLOB_SHA256 = "9c7de8995a08602186c7090081bbfc10b7c51170ad7e544f2f2dc71333b4f21d"
M286_SHA256 = "f7069c6d5fe11d40e302b57ab1f2ca0c82174a312e31264c64fa3e9db44e20ba"
M287_SHA256 = "e196ed5bb25882aa890dcda4a10aecd7abd4503b0288f4d3cc47abacc09ae134"


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
    messages = [{"role": "user", "content": [{"type": "video"}, {"type": "text", "text": prompt}]}]
    rendered = processor.apply_chat_template(messages, tokenize=False, add_generation_prompt=True)
    return processor(text=[rendered], videos=[images], return_tensors="pt", padding=True)


def binary_probabilities(no_logit: float, yes_logit: float) -> tuple[float, float]:
    peak = max(no_logit, yes_logit)
    no_exp = math.exp(no_logit - peak)
    yes_exp = math.exp(yes_logit - peak)
    total = no_exp + yes_exp
    return no_exp / total, yes_exp / total


def binary_js_divergence(left: tuple[float, float], right: tuple[float, float]) -> float:
    middle = tuple((a + b) / 2.0 for a, b in zip(left, right))
    def kl(values, target):
        return sum(value * math.log(value / other) for value, other in zip(values, target) if value > 0.0)
    return 0.5 * kl(left, middle) + 0.5 * kl(right, middle)


def knife_metrics(records: list[dict]) -> dict:
    tp = sum(item["expected"] == 1 and item["decision"] == 1 for item in records)
    fn = sum(item["expected"] == 1 and item["decision"] == 0 for item in records)
    fp = sum(item["expected"] == 0 and item["decision"] == 1 for item in records)
    tn = sum(item["expected"] == 0 and item["decision"] == 0 for item in records)
    return {
        "tp": tp, "fn": fn, "fp": fp, "tn": tn,
        "recall": None if tp + fn == 0 else tp / (tp + fn),
        "false_alarm_rate": None if fp + tn == 0 else fp / (fp + tn),
        "accuracy": (tp + tn) / len(records),
    }


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
    m286_path = root / "M286_M120_A8_NATURAL_PROMPT_SWEEP_RESULT.json"
    m287_path = root / "M287_NATURAL_PROMPT_BOARD_RESULT_02.json"
    if sha256(m286_path) != M286_SHA256 or sha256(m287_path) != M287_SHA256:
        raise RuntimeError("M289 predecessor identity mismatch")

    sys.path[:0] = [
        str(workspace), str(workspace / "scripts"), str(root / "scripts"),
        str(root / "m273_latest_binary_source"), str(root / "m246_knife_binary_source"),
    ]
    from m264_gpu_resolution_semantic_suite import build_samples
    from m266_gpu_multiscale_semantic_gate import multiscale_views
    from m246_knife_binary import KNIFE_NO_TOKEN_ID, KNIFE_PROMPT, KNIFE_YES_TOKEN_ID
    from mage_a8_runtime import install_packed_linear_a8_hooks
    from packed_checkpoint_artifact import load_packed_checkpoint

    import torch
    from transformers import AutoModelForCausalLM, AutoProcessor

    plain_exact = "Is a knife visible? Reply with exactly 1 for yes or 0 for no:"
    plain_minimal = "Knife visible? Answer only 1 or 0:"
    configurations = [
        {"baseline": "fixed_high_quality", "prompt": KNIFE_PROMPT, "view_indices": [0, 1, 2, 3], "pruning_ratio": 0.0},
        {"baseline": "fixed_ratio_visual_pruning", "prompt": KNIFE_PROMPT, "view_indices": [2, 3], "pruning_ratio": 0.5},
        {"baseline": "token_count_aware", "prompt": plain_minimal, "view_indices": [2, 3], "pruning_ratio": 0.5},
        {"baseline": "bact", "prompt": plain_exact, "view_indices": [2, 3], "pruning_ratio": 0.5},
    ]

    torch.set_num_threads(args.threads)
    result = {
        "date": "2026-09-02",
        "gate": "M289-M120-A8-four-BACT-baseline-small-screen",
        "status": "FAIL",
        "classification": (
            "Four frozen baseline definitions evaluated under one exact M120+A8 software reference on four "
            "small labelled examples. This is neither held-out target-scene accuracy nor FPGA timing/resources/power."
        ),
        "m286_sha256": sha256(m286_path),
        "m287_sha256": sha256(m287_path),
    }
    handles = []
    started = time.perf_counter()
    try:
        processor = AutoProcessor.from_pretrained(args.model.resolve(), trust_remote_code=True, local_files_only=True)
        model = AutoModelForCausalLM.from_pretrained(
            args.model.resolve(), trust_remote_code=True, local_files_only=True,
            torch_dtype=torch.bfloat16, low_cpu_mem_usage=True,
            attn_implementation="eager", device_map={"": "cpu"},
        ).eval()
        checkpoint = args.checkpoint.resolve()
        manifest_path = checkpoint / "CHECKPOINT_MANIFEST.json"
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        if sha256(manifest_path) != M120_MANIFEST_SHA256 or manifest["blob"]["sha256"] != M120_BLOB_SHA256:
            raise RuntimeError("M289 M120 checkpoint identity mismatch")
        reload_info = load_packed_checkpoint(torch, model, checkpoint, verify_blob=True, row_chunk=32)
        handles, hook_names = install_packed_linear_a8_hooks(
            torch, model, checkpoint, r"^(model\.language_model\.layers\.|lm_head$)"
        )
        if len(hook_names) != 253:
            raise RuntimeError(f"M289 A8 hook closure mismatch {len(hook_names)}")

        samples = build_samples(workspace, args.examples.resolve())
        all_views = {sample.name: multiscale_views(sample.frames_448) for sample in samples}
        outputs = []
        for configuration in configurations:
            records = []
            token_count = None
            for sample in samples:
                views = all_views[sample.name][configuration["view_indices"]]
                inputs = prepare(processor, views, configuration["prompt"])
                observed = int(inputs["input_ids"].shape[1])
                token_count = observed if token_count is None else token_count
                if observed != token_count:
                    raise RuntimeError("M289 token geometry changed across samples")
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
                    "name": sample.name, "expected": expected, "decision": decision,
                    "pass": finite and decision == expected, "finite": finite,
                    "no_logit": no_logit, "yes_logit": yes_logit,
                    "margin_yes_minus_no": yes_logit - no_logit,
                    "binary_probabilities_no_yes": list(binary_probabilities(no_logit, yes_logit)),
                    "forward_ms": (time.perf_counter() - probe_started) * 1000.0,
                })
            batches = math.ceil(int(token_count) / 32)
            outputs.append({
                **configuration,
                "prompt_tokens": int(token_count),
                "visual_tokens": len(configuration["view_indices"]) * 49,
                "t32_batches": batches,
                "logical_fpga_calls": 154 * batches + 8,
                "records": records,
                "all_finite": all(item["finite"] for item in records),
                "knife_metrics_small_screen": knife_metrics(records),
                "minimum_absolute_binary_margin": min(abs(item["margin_yes_minus_no"]) for item in records),
            })

        reference = {item["name"]: tuple(item["binary_probabilities_no_yes"]) for item in outputs[0]["records"]}
        for output in outputs:
            divergences = [
                binary_js_divergence(reference[item["name"]], tuple(item["binary_probabilities_no_yes"]))
                for item in output["records"]
            ]
            output["semantic_loss_proxy"] = {
                "definition": "mean binary Jensen-Shannon divergence from fixed_high_quality over frozen screen",
                "per_sample": divergences,
                "mean": sum(divergences) / len(divergences),
                "calibrated_accuracy": False,
            }

        pass_small = all(
            item["all_finite"] and item["knife_metrics_small_screen"]["accuracy"] == 1.0
            for item in outputs
        )
        result.update({
            "status": "PASS_FOUR_BASELINE_SMALL_SCREEN" if pass_small else "FAIL_FOUR_BASELINE_SMALL_SCREEN",
            "model": "microsoft/Mage-VL",
            "backend": "WSL CPU exact reconstructed M120 weights plus 253 A8-G64 hooks",
            "checkpoint": reload_info,
            "sample_count": len(samples),
            "baselines": outputs,
            "fixed_ratio_definition": (
                "50% visual-view pruning while retaining the exact fixed-high-quality prompt; selected before "
                "examining T32 batch boundaries."
            ),
            "action_macro_f1_available": False,
            "joint_quality_gate_passed": False,
            "joint_quality_gate_reason": (
                "The four-sample binary screen has no complete action labels/predictions and is not a held-out "
                "target-camera dataset. It can freeze candidates, not satisfy the final quality constraint."
            ),
            "semantic_accuracy_passed": False,
            "board_execution_run": False,
            "active_board_service_changed": False,
            "boot_dtb_cma_partitions_changed": False,
            "stable_rollback_preserved": True,
            "next_gate": (
                "Create source-video-disjoint calibration/test manifests with knife episodes and all five action "
                "classes; freeze thresholds/configuration on calibration, then run test exactly once."
            ),
        })
    except BaseException as exc:
        result["error"] = f"{type(exc).__name__}: {exc}"
        result["next_gate"] = "Fix and rerun M289 at the same offline level; do not touch the board."
    finally:
        for handle in reversed(handles):
            handle.remove()
        result["wall_ms"] = (time.perf_counter() - started) * 1000.0
        result["source_sha256"] = sha256(Path(__file__).resolve())
        atomic_json(args.result, result)
        print(json.dumps(result, ensure_ascii=False), flush=True)

    marker = "PASS" if result["status"] == "PASS_FOUR_BASELINE_SMALL_SCREEN" else "FAIL"
    print(f"M289_FOUR_BASELINE_SCREEN_{marker}", flush=True)
    return 0 if marker == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
