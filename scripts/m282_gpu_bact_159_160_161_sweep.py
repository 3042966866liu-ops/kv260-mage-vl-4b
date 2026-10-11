#!/usr/bin/env python3
"""Official-GPU semantic/numerical screen for exact M281 boundary prompts."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
import time
from pathlib import Path

from PIL import Image

from m264_gpu_resolution_semantic_suite import build_samples


EXPECTED_M281_SHA256 = "d80807387c529a7cbddffaebc6721f8bcbb5a653b8e38ae38dbda22be20fd074"


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


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


def tensor_fp16_sha256(tensor) -> str:
    values = tensor.detach().float().half().cpu().contiguous().numpy()
    return hashlib.sha256(values.tobytes(order="C")).hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--workspace", type=Path, required=True)
    parser.add_argument("--model", type=Path, required=True)
    parser.add_argument("--examples", type=Path, required=True)
    parser.add_argument("--result", type=Path, required=True)
    args = parser.parse_args()
    workspace = args.workspace.resolve()
    root = workspace / "deployment/mage_vl4b"
    m281_path = root / "M281_BACT_159_160_161_GEOMETRY_RESULT.json"
    if sha256(m281_path) != EXPECTED_M281_SHA256:
        raise RuntimeError("M282 M281 predecessor hash mismatch")
    m281 = json.loads(m281_path.read_text(encoding="utf-8"))
    if m281.get("status") != "PASS_OFFLINE_GEOMETRY_ONLY":
        raise RuntimeError("M282 requires M281 geometry PASS")

    source = root / "m281_bact_boundary_source"
    m273_source = root / "m273_latest_binary_source"
    m246_source = root / "m246_knife_binary_source"
    sys.path.insert(0, str(source))
    sys.path.insert(0, str(m273_source))
    sys.path.insert(0, str(m246_source))
    from m273_latest_multiscale_contract import make_views
    from m281_boundary_contract import PROMPTS
    from m246_knife_binary import KNIFE_NO_TOKEN_ID, KNIFE_YES_TOKEN_ID

    import torch
    from transformers import AutoModelForCausalLM, AutoProcessor, BitsAndBytesConfig

    if not torch.cuda.is_available():
        raise RuntimeError("M282 requires the existing WSL CUDA environment")
    model_path = args.model.resolve()
    quant = BitsAndBytesConfig(
        load_in_4bit=True,
        bnb_4bit_quant_type="nf4",
        bnb_4bit_use_double_quant=True,
        bnb_4bit_compute_dtype=torch.bfloat16,
    )
    load_started = time.perf_counter()
    processor = AutoProcessor.from_pretrained(
        model_path, trust_remote_code=True, local_files_only=True
    )
    model = AutoModelForCausalLM.from_pretrained(
        model_path,
        trust_remote_code=True,
        local_files_only=True,
        quantization_config=quant,
        device_map="auto",
        low_cpu_mem_usage=True,
    ).eval()
    load_ms = (time.perf_counter() - load_started) * 1000.0
    samples = build_samples(workspace, args.examples.resolve())

    candidates = []
    all_finite = True
    all_geometry = True
    for target in (159, 160, 161):
        prompt = PROMPTS[target]
        records = []
        for sample in samples:
            views = make_views(sample.frames_448[-1:])
            inputs = prepare(processor, views, prompt)
            moved = {
                key: value.to("cuda") if hasattr(value, "to") else value
                for key, value in inputs.items()
            }
            started = time.perf_counter()
            with torch.inference_mode():
                output = model(**moved, use_cache=False)
            last_logits = output.logits[0, -1].float()
            finite = bool(torch.isfinite(last_logits).all().item())
            no_logit = float(last_logits[KNIFE_NO_TOKEN_ID].item())
            yes_logit = float(last_logits[KNIFE_YES_TOKEN_ID].item())
            expected = 1 if sample.expected.knife == "有" else 0
            decision = 1 if yes_logit >= no_logit else 0
            observed_tokens = int(moved["input_ids"].shape[1])
            all_finite = all_finite and finite
            all_geometry = all_geometry and observed_tokens == target
            records.append({
                "name": sample.name,
                "expected": expected,
                "decision": decision,
                "pass": decision == expected,
                "finite": finite,
                "no_logit": no_logit,
                "yes_logit": yes_logit,
                "margin_yes_minus_no": yes_logit - no_logit,
                "absolute_decision_margin": abs(yes_logit - no_logit),
                "prompt_tokens": observed_tokens,
                "last_logits_sha256_fp16": tensor_fp16_sha256(last_logits),
                "forward_ms": (time.perf_counter() - started) * 1000.0,
            })
        candidates.append({
            "target_prompt_tokens": target,
            "prompt": prompt,
            "t32_batches": (target + 31) // 32,
            "expected_logical_fpga_calls": 154 * ((target + 31) // 32) + 8,
            "records": records,
            "suite_pass": len(records) == 4 and all(item["pass"] for item in records),
            "finite_pass": all(item["finite"] for item in records),
            "geometry_pass": all(item["prompt_tokens"] == target for item in records),
            "minimum_absolute_margin": min(
                item["absolute_decision_margin"] for item in records
            ),
        })

    suite_pass = (
        all_finite
        and all_geometry
        and len(candidates) == 3
        and all(item["suite_pass"] for item in candidates)
    )
    result = {
        "date": "2026-09-02",
        "gate": "M282-official-GPU-BACT-159-160-161-screen",
        "status": "PASS_SMALL_SCREEN" if suite_pass else "FAIL_SMALL_SCREEN",
        "classification": (
            "Official Mage-VL NF4/BF16 GPU fixed four-sample boundary-prompt screen; "
            "not the KV260 quantized numerical reference, held-out accuracy, comparative "
            "board timing, power, Web or real-time evidence."
        ),
        "m281_sha256": sha256(m281_path),
        "model": "microsoft/Mage-VL",
        "checkpoint_config_sha256": sha256(model_path / "config.json"),
        "backend": "WSL local CUDA GPU; not KV260",
        "quantization": "bitsandbytes NF4 4-bit; BF16 compute",
        "gpu": torch.cuda.get_device_name(0),
        "load_ms": load_ms,
        "candidates": candidates,
        "all_finite": all_finite,
        "all_exact_geometry": all_geometry,
        "suite_pass": suite_pass,
        "semantic_accuracy_passed": False,
        "threshold_calibrated": False,
        "model_execution_run": True,
        "board_execution_run": False,
        "active_board_service_changed": False,
        "boot_dtb_cma_partitions_changed": False,
        "stable_rollback_preserved": True,
        "rejected_attempts": [
            {
                "attempt": "01",
                "status": "STOPPED_BEFORE_MODEL_LOAD",
                "reason": (
                    "WSL wrapper omitted the explicit m276_short_prompt_source PYTHONPATH "
                    "entry required by m281_boundary_contract. The wrapper now performs a "
                    "local-module import preflight before loading the model."
                ),
                "model_forward_run": False,
                "board_contacted": False,
            }
        ],
        "source_sha256": sha256(Path(__file__).resolve()),
        "next_gate": (
            "If PASS, build per-fixture references through the unchanged quantized M276 "
            "runtime without repeating kernel CSim; only then package a controlled COM3 "
            "159/160/161 timing gate. If FAIL, replace probe suffixes and rerun M281/M282."
        ),
    }
    args.result.parent.mkdir(parents=True, exist_ok=True)
    partial = args.result.with_suffix(args.result.suffix + ".partial")
    partial.write_text(
        json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    os.replace(partial, args.result)
    print(
        f"M282_BACT_GPU_SCREEN_{'PASS' if suite_pass else 'FAIL'} "
        + " ".join(
            f"{item['target_prompt_tokens']}:{item['suite_pass']}:"
            f"{item['minimum_absolute_margin']:.6f}"
            for item in candidates
        )
    )
    return 0 if suite_pass else 1


if __name__ == "__main__":
    raise SystemExit(main())
