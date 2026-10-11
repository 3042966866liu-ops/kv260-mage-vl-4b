#!/usr/bin/env python3
"""Diagnose M283 with the exact M120 weights plus A8-G64 on the host CPU.

This is deliberately a one-fixture diagnostic.  It does not promote the
artificial ``x`` suffixes to natural monitoring prompts or to accuracy data.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
import time
from pathlib import Path

from PIL import Image


M120_MANIFEST_SHA256 = "5ff33d1922376e18277902a8b051d069315f79c11b4f63e8d72517acd1dcd5d0"
M120_BLOB_SHA256 = "9c7de8995a08602186c7090081bbfc10b7c51170ad7e544f2f2dc71333b4f21d"
M282_SHA256 = "a42cde7a03d944f66f9fdad362ce60036393b82188f724fdb8c61236b97a2cbf"
M283_SHA256 = "65e13a0f0c6041560bddf4349bbcd0ffb4b5b113d40826e425cedb723c824a79"


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
    m282_path = root / "M282_GPU_BACT_159_160_161_RESULT.json"
    m283_path = root / "M283_BACT_BOUNDARY_BOARD_RESULT_02.json"
    if sha256(m282_path) != M282_SHA256 or sha256(m283_path) != M283_SHA256:
        raise RuntimeError("M285 predecessor identity mismatch")

    sys.path[:0] = [
        str(workspace / "scripts"),
        str(root / "scripts"),
        str(root / "m281_bact_boundary_source"),
        str(root / "m276_short_prompt_source"),
        str(root / "m273_latest_binary_source"),
        str(root / "m246_knife_binary_source"),
    ]
    from m264_gpu_resolution_semantic_suite import build_samples
    from m273_latest_multiscale_contract import make_views
    from m281_boundary_contract import PROMPTS
    from m246_knife_binary import KNIFE_NO_TOKEN_ID, KNIFE_YES_TOKEN_ID
    from mage_a8_runtime import install_packed_linear_a8_hooks
    from packed_checkpoint_artifact import load_packed_checkpoint

    import torch
    from transformers import AutoModelForCausalLM, AutoProcessor

    torch.set_num_threads(args.threads)
    checkpoint = args.checkpoint.resolve()
    checkpoint_manifest = checkpoint / "CHECKPOINT_MANIFEST.json"
    if sha256(checkpoint_manifest) != M120_MANIFEST_SHA256:
        raise RuntimeError("M285 exact M120 manifest hash mismatch")
    manifest = json.loads(checkpoint_manifest.read_text(encoding="utf-8"))
    if manifest.get("blob", {}).get("sha256") != M120_BLOB_SHA256:
        raise RuntimeError("M285 exact M120 blob declaration mismatch")

    result = {
        "date": "2026-09-02",
        "gate": "M285-M120-A8-artificial-boundary-single-fixture-diagnostic",
        "status": "FAIL",
        "classification": (
            "One-fixture exact M120 mixed-weight plus A8-G64 CPU diagnostic for the "
            "M283 artificial prompts; not FPGA execution, target-scene accuracy, "
            "natural-prompt validation, timing comparison, power, Web or real-time evidence."
        ),
        "m282_sha256": sha256(m282_path),
        "m283_sha256": sha256(m283_path),
    }
    started = time.perf_counter()
    handles = []
    try:
        processor = AutoProcessor.from_pretrained(
            args.model.resolve(), trust_remote_code=True, local_files_only=True
        )
        print("[M285] loading BF16 model shell on CPU", flush=True)
        model = AutoModelForCausalLM.from_pretrained(
            args.model.resolve(),
            trust_remote_code=True,
            local_files_only=True,
            torch_dtype=torch.bfloat16,
            low_cpu_mem_usage=True,
            attn_implementation="eager",
            device_map={"": "cpu"},
        ).eval()
        print("[M285] loading and verifying exact M120 checkpoint", flush=True)
        reload_info = load_packed_checkpoint(
            torch, model, checkpoint, verify_blob=True, row_chunk=32
        )
        if reload_info["manifest_sha256"] != M120_MANIFEST_SHA256:
            raise RuntimeError("M285 reloaded M120 manifest mismatch")
        if reload_info["blob_sha256"] != M120_BLOB_SHA256:
            raise RuntimeError("M285 reloaded M120 blob mismatch")
        handles, names = install_packed_linear_a8_hooks(
            torch, model, checkpoint, r"^(model\.language_model\.layers\.|lm_head$)"
        )
        if len(names) != 253:
            raise RuntimeError(f"M285 A8 hook closure mismatch {len(names)}")

        samples = build_samples(workspace, args.examples.resolve())
        selected = [item for item in samples if item.name == "motorcycle_person_no_knife"]
        if len(selected) != 1:
            raise RuntimeError("M285 frozen motorcycle fixture identity mismatch")
        views = make_views(selected[0].frames_448[-1:])
        records = []
        for target in (159, 160, 161):
            inputs = prepare(processor, views, PROMPTS[target])
            token_count = int(inputs["input_ids"].shape[1])
            if token_count != target:
                raise RuntimeError(
                    f"M285 token geometry mismatch target={target} observed={token_count}"
                )
            probe_started = time.perf_counter()
            with torch.inference_mode():
                output = model(**inputs, use_cache=False)
            logits = output.logits[0, -1].to(dtype=torch.float32, device="cpu").contiguous()
            finite = bool(torch.isfinite(logits).all().item())
            no_logit = float(logits[KNIFE_NO_TOKEN_ID].item())
            yes_logit = float(logits[KNIFE_YES_TOKEN_ID].item())
            decision = 1 if yes_logit >= no_logit else 0
            records.append({
                "prompt_tokens": target,
                "finite": finite,
                "decision": decision,
                "no_logit": no_logit,
                "yes_logit": yes_logit,
                "margin_yes_minus_no": yes_logit - no_logit,
                "logits_sha256_fp32": hashlib.sha256(
                    logits.numpy().astype("<f4", copy=False).tobytes()
                ).hexdigest(),
                "forward_ms": (time.perf_counter() - probe_started) * 1000.0,
            })

        decisions = [item["decision"] for item in records]
        all_finite = all(item["finite"] for item in records)
        board_decisions = [0, 1, 0]
        result.update({
            "status": "MEASURED",
            "model": "microsoft/Mage-VL",
            "backend": "WSL CPU exact reconstructed M120 weights plus A8-G64 hooks",
            "checkpoint": reload_info,
            "a8_hook_count": len(names),
            "fixture": "motorcycle_person_no_knife",
            "records": records,
            "all_finite": all_finite,
            "m120_a8_decisions": decisions,
            "m283_board_decisions": board_decisions,
            "decision_pattern_matches_board": decisions == board_decisions,
            "semantic_invariance_passed": decisions == [0, 0, 0],
            "diagnostic_interpretation": (
                "If the decision pattern matches M283, the artificial-prompt flip is "
                "reproduced by the same quantized software policy. Otherwise a board versus "
                "same-quantized differential trace is required before attributing the flip."
            ),
            "board_execution_run": False,
            "active_board_service_changed": False,
            "boot_dtb_cma_partitions_changed": False,
            "stable_rollback_preserved": True,
            "next_gate": (
                "Use this diagnosis to choose either prompt-policy redesign or a board-vs-"
                "same-quantized differential trace. Natural labelled BACT configurations "
                "remain a separate accuracy experiment."
            ),
        })
    except BaseException as exc:
        result["error"] = f"{type(exc).__name__}: {exc}"
        result["next_gate"] = "Fix and rerun this same offline diagnostic; do not touch the board."
    finally:
        for handle in reversed(handles):
            handle.remove()
        result["wall_ms"] = (time.perf_counter() - started) * 1000.0
        result["source_sha256"] = sha256(Path(__file__).resolve())
        atomic_json(args.result, result)
        print(json.dumps(result, ensure_ascii=False), flush=True)

    print("M285_M120_A8_DIAGNOSTIC_MEASURED" if result["status"] == "MEASURED" else "M285_M120_A8_DIAGNOSTIC_FAIL", flush=True)
    return 0 if result["status"] == "MEASURED" else 1


if __name__ == "__main__":
    raise SystemExit(main())
