#!/usr/bin/env python3
"""Screen W2->W4 language-family upgrades against the official BF16 model.

This is an offline policy-search gate, not an FPGA or deployment gate.  It
keeps the current M56 W2/W4+A8 policy fixed, upgrades exactly one early-layer
family at a time from W2 to an exhaustive FP16-scale W4 reconstruction of the
official weight, and measures the complete model against one frozen BF16 text
case.  The resulting family ranking is a screening result; selected families
must subsequently pass a layer-level scan and a frozen multi-case quality
suite before a new packed checkpoint may be built.
"""

from __future__ import annotations

import argparse
import gc
import hashlib
import json
import math
import os
import sys
import time
from pathlib import Path


LAYERS = 36
EARLY_W2_LAYERS = tuple(range(10))
FAMILIES = {
    "qkv": ("self_attn.q_proj", "self_attn.k_proj", "self_attn.v_proj"),
    "attention_out": ("self_attn.o_proj",),
    "gate_up": ("mlp.gate_proj", "mlp.up_proj"),
    "mlp_down": ("mlp.down_proj",),
}


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(8 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def atomic_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(
        json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    os.replace(temporary, path)


def metrics(torch, observed, reference) -> dict[str, object]:
    observed = observed.detach().to(dtype=torch.float64, device="cpu")
    reference = reference.detach().to(dtype=torch.float64, device="cpu")
    if tuple(observed.shape) != tuple(reference.shape):
        raise RuntimeError(f"shape mismatch {tuple(observed.shape)} != {tuple(reference.shape)}")
    delta = observed - reference
    ref_norm = max(float(torch.linalg.vector_norm(reference)), 1.0e-12)
    obs_norm = max(float(torch.linalg.vector_norm(observed)), 1.0e-12)
    return {
        "shape": list(observed.shape),
        "finite": bool(torch.isfinite(observed).all()),
        "max_abs": float(delta.abs().max()),
        "mean_abs": float(delta.abs().mean()),
        "rmse": float(torch.sqrt(torch.mean(delta * delta))),
        "relative_l2": float(torch.linalg.vector_norm(delta) / ref_norm),
        "cosine": float(
            torch.vdot(observed.reshape(-1), reference.reshape(-1))
            / (obs_norm * ref_norm)
        ),
    }


def module_name(layer: int, suffix: str) -> str:
    return f"model.language_model.layers.{layer}.{suffix}"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--model", type=Path, required=True)
    parser.add_argument("--checkpoint", type=Path, required=True)
    parser.add_argument("--deps", type=Path, required=True)
    parser.add_argument("--reference", type=Path, required=True)
    parser.add_argument("--auxiliary", type=Path, required=True)
    parser.add_argument("--auxiliary-manifest", type=Path, required=True)
    parser.add_argument("--result", type=Path, required=True)
    parser.add_argument("--row-chunk", type=int, default=32)
    parser.add_argument(
        "--variants",
        default="baseline,qkv,attention_out,gate_up,mlp_down",
        help="comma-separated subset of baseline,qkv,attention_out,gate_up,mlp_down",
    )
    parser.add_argument(
        "--scan-mode",
        choices=("family", "layer", "cumulative"),
        default="family",
        help="family upgrades all early W2 layers; layer upgrades one early layer per selected family",
    )
    parser.add_argument("--ranking-result", type=Path)
    parser.add_argument(
        "--activation-policy",
        choices=("a8", "bf16"),
        default="a8",
        help="a8 reproduces the current FPGA input QDQ; bf16 is a PS/high-precision diagnostic",
    )
    parser.add_argument(
        "--cumulative-steps",
        default="1,2,3,4,6,8,10,12,15,20",
        help="prefix lengths from ranking-result used by cumulative mode",
    )
    args = parser.parse_args()

    sys.path.insert(0, str(args.deps.resolve()))
    import numpy as np
    import torch
    from safetensors import safe_open
    from transformers import AutoModelForCausalLM

    from mage_a8_runtime import install_packed_linear_a8_hooks
    from mixed_bit_checkpoint import recover_full_range_rows_for_storage
    from packed_checkpoint_artifact import load_packed_checkpoint

    started = time.perf_counter()
    result: dict[str, object] = {
        "date": "2026-08-31",
        "gate": {
            "family": "M103-M56-early-language-family-W2-to-W4-sensitivity-screen",
            "layer": "M104-M56-early-language-layer-W2-to-W4-sensitivity-screen",
            "cumulative": "M105-M56-cumulative-mixed-precision-Pareto-screen",
        }[args.scan_mode],
        "status": "FAIL",
        "classification": (
            "offline single-case family-level policy screen; not a quantization-quality PASS, "
            "not FPGA evidence, and not permission to enter text E2E, video, or Web"
        ),
    }
    capture_handles = []
    a8_handles = []
    auxiliary_npz = None
    try:
        requested_variants = [item.strip() for item in args.variants.split(",") if item.strip()]
        allowed = {"baseline", *FAMILIES}
        if not requested_variants or len(requested_variants) != len(set(requested_variants)):
            raise RuntimeError("variants must be a non-empty unique list")
        if set(requested_variants) - allowed:
            raise RuntimeError(f"unknown variants: {sorted(set(requested_variants) - allowed)}")
        if requested_variants[0] != "baseline":
            raise RuntimeError("baseline must be the first variant")

        reference = json.loads(args.reference.read_text(encoding="utf-8"))
        prompt_ids = [int(value) for value in reference["prompt_token_ids"]]
        frozen_official_token = int(reference["generated_token_ids"][0])
        if len(prompt_ids) != 30:
            raise RuntimeError("frozen reference must contain 30 prompt tokens")

        aux_manifest = json.loads(args.auxiliary_manifest.read_text(encoding="utf-8"))
        if aux_manifest.get("result") != "PASS":
            raise RuntimeError("auxiliary manifest is not PASS")
        if sha256(args.auxiliary) != aux_manifest.get("payload_sha256"):
            raise RuntimeError("auxiliary payload hash mismatch")

        index_path = args.model / "model.safetensors.index.json"
        index = json.loads(index_path.read_text(encoding="utf-8"))
        weight_map = index["weight_map"]

        print("[M103] loading official BF16 model", flush=True)
        model = AutoModelForCausalLM.from_pretrained(
            args.model,
            trust_remote_code=True,
            local_files_only=True,
            torch_dtype=torch.bfloat16,
            low_cpu_mem_usage=True,
            attn_implementation="eager",
            device_map={"": "cpu"},
        ).eval()
        modules = dict(model.named_modules())
        parameters = dict(model.named_parameters())

        family_inputs: dict[str, object] = {}
        layer_outputs: dict[str, object] = {}

        def family_hook(logical: str):
            def hook(_module, positional):
                value = positional[0].detach().to(dtype=torch.float32, device="cpu")
                family_inputs[logical] = value[0].contiguous()
            return hook

        def layer_hook(logical: str):
            def hook(_module, _positional, output):
                value = output[0] if isinstance(output, (tuple, list)) else output
                layer_outputs[logical] = value.detach().to(dtype=torch.float32, device="cpu")[0].contiguous()
            return hook

        for layer in range(LAYERS):
            for family, suffixes in FAMILIES.items():
                actual = module_name(layer, suffixes[0])
                capture_handles.append(
                    modules[actual].register_forward_pre_hook(
                        family_hook(f"layer{layer:02d}_{family}")
                    )
                )
            layer_actual = f"model.language_model.layers.{layer}"
            capture_handles.append(
                modules[layer_actual].register_forward_hook(layer_hook(f"layer{layer:02d}"))
            )

        input_ids = torch.tensor([prompt_ids], dtype=torch.long)
        attention_mask = torch.ones_like(input_ids)

        def run_once(label: str):
            family_inputs.clear()
            layer_outputs.clear()
            run_started = time.perf_counter()
            with torch.inference_mode():
                output = model(
                    input_ids=input_ids,
                    attention_mask=attention_mask,
                    use_cache=False,
                    return_dict=True,
                )
            logits = output.logits[0, -1].detach().to(dtype=torch.float32, device="cpu")
            if len(family_inputs) != LAYERS * len(FAMILIES):
                raise RuntimeError(f"{label}: family capture incomplete {len(family_inputs)}")
            if len(layer_outputs) != LAYERS:
                raise RuntimeError(f"{label}: layer capture incomplete {len(layer_outputs)}")
            return {
                "label": label,
                "logits": logits,
                "families": {name: value.clone() for name, value in family_inputs.items()},
                "layers": {name: value.clone() for name, value in layer_outputs.items()},
                "inference_ms": (time.perf_counter() - run_started) * 1000.0,
            }

        official = run_once("official_bf16")
        official_token = int(torch.argmax(official["logits"]))
        if official_token != frozen_official_token:
            raise RuntimeError(
                f"official token drift: fresh={official_token} frozen={frozen_official_token}"
            )
        official_top5 = [int(value) for value in torch.topk(official["logits"], 5).indices]
        print(f"[M103] official token={official_token} top5={official_top5}", flush=True)

        print("[M103] loading exact M56 checkpoint", flush=True)
        reload_info = load_packed_checkpoint(
            torch, model, args.checkpoint, verify_blob=True, row_chunk=args.row_chunk
        )

        # The fixed board text path obtains the used rows from the official
        # embedding.  Keep that same high-precision PS boundary in every screen.
        auxiliary_npz = np.load(args.auxiliary, allow_pickle=False)
        embedding_rows = torch.from_numpy(
            np.asarray(
                auxiliary_npz["model.language_model.embed_tokens.weight"], dtype=np.float32
            )
        ).to(torch.bfloat16)
        embedding_ids = [int(value) for value in aux_manifest["selected_embedding_ids"]]
        with torch.no_grad():
            model.get_input_embeddings().weight[
                torch.tensor(embedding_ids, dtype=torch.long)
            ] = embedding_rows

        if args.activation_policy == "a8":
            a8_handles, a8_names = install_packed_linear_a8_hooks(
                torch,
                model,
                args.checkpoint,
                r"^(model\.language_model\.layers\.|lm_head$)",
            )
        else:
            a8_names = []

        def summarize_run(run, upgraded_modules: list[str], added_code_bytes: int):
            logits = run["logits"]
            token = int(torch.argmax(logits))
            top5 = [int(value) for value in torch.topk(logits, 5).indices]
            layer_metrics = {
                name: metrics(torch, run["layers"][name], official["layers"][name])
                for name in sorted(official["layers"])
            }
            family_metrics = {
                name: metrics(torch, run["families"][name], official["families"][name])
                for name in sorted(official["families"])
            }
            family_aggregates = {}
            for family in FAMILIES:
                members = [family_metrics[f"layer{layer:02d}_{family}"] for layer in range(LAYERS)]
                family_aggregates[family] = {
                    "median_relative_l2": float(np.median([item["relative_l2"] for item in members])),
                    "max_relative_l2": max(item["relative_l2"] for item in members),
                    "minimum_cosine": min(item["cosine"] for item in members),
                    "max_abs": max(item["max_abs"] for item in members),
                }
            return {
                "upgraded_modules": upgraded_modules,
                "upgraded_module_count": len(upgraded_modules),
                "added_weight_code_bytes_vs_W2": added_code_bytes,
                "inference_ms": run["inference_ms"],
                "generated_token_id": token,
                "token_matches_bf16": token == official_token,
                "top5_token_ids": top5,
                "top1_in_bf16_top5": token in official_top5,
                "top5_overlap_count": len(set(top5) & set(official_top5)),
                "logits": metrics(torch, logits, official["logits"]),
                "final_layer": layer_metrics[f"layer{LAYERS - 1:02d}"],
                "layer_metrics": layer_metrics,
                "family_input_aggregates": family_aggregates,
            }

        variants = {}
        baseline_run = run_once("baseline_m56")
        variants["baseline"] = summarize_run(baseline_run, [], 0)
        baseline_logit_relative_l2 = variants["baseline"]["logits"]["relative_l2"]
        print(
            f"[M103] baseline token={variants['baseline']['generated_token_id']} "
            f"logit_rel={baseline_logit_relative_l2:.6f}",
            flush=True,
        )
        del baseline_run
        gc.collect()

        def official_weight(parameter_name: str):
            shard_name = weight_map.get(parameter_name)
            if shard_name is None:
                raise RuntimeError(f"official weight not indexed: {parameter_name}")
            with safe_open(str(args.model / shard_name), framework="pt", device="cpu") as handle:
                return handle.get_tensor(parameter_name)

        if args.scan_mode == "family":
            scan_tasks = [
                (
                    family,
                    family,
                    EARLY_W2_LAYERS,
                    [
                        module_name(layer, suffix)
                        for layer in EARLY_W2_LAYERS
                        for suffix in FAMILIES[family]
                    ],
                )
                for family in requested_variants[1:]
            ]
        elif args.scan_mode == "layer":
            scan_tasks = [
                (
                    f"{family}_layer{layer:02d}",
                    family,
                    (layer,),
                    [module_name(layer, suffix) for suffix in FAMILIES[family]],
                )
                for family in requested_variants[1:]
                for layer in EARLY_W2_LAYERS
            ]
        else:
            if args.ranking_result is None:
                raise RuntimeError("cumulative mode requires --ranking-result")
            ranking_payload = json.loads(args.ranking_result.read_text(encoding="utf-8"))
            if ranking_payload.get("status") != "MEASURED_SCREEN_ONLY":
                raise RuntimeError("ranking result is not a measured screen")
            ranking = list(ranking_payload.get("benefit_per_storage_ranking", []))
            ranking_variants = ranking_payload.get("variants", {})
            if not ranking or any(name not in ranking_variants for name in ranking):
                raise RuntimeError("ranking result is incomplete")
            steps = sorted(
                {
                    int(value)
                    for value in args.cumulative_steps.split(",")
                    if value.strip()
                }
            )
            if not steps or steps[0] < 1 or steps[-1] > len(ranking):
                raise RuntimeError("cumulative steps exceed ranking bounds")
            scan_tasks = []
            for step in steps:
                prefix = ranking[:step]
                targets = sorted(
                    {
                        target
                        for ranked_name in prefix
                        for target in ranking_variants[ranked_name]["upgraded_modules"]
                    }
                )
                layers = sorted(
                    {
                        int(layer)
                        for ranked_name in prefix
                        for layer in ranking_variants[ranked_name].get("layers", [])
                    }
                )
                scan_tasks.append((f"top{step:02d}", "cumulative", tuple(layers), targets))

        for variant_name, family, target_layers, targets in scan_tasks:
            backups = {}
            added_code_bytes = 0
            try:
                print(f"[M103] upgrading family={family} modules={len(targets)}", flush=True)
                for index, target in enumerate(targets, start=1):
                    parameter_name = f"{target}.weight"
                    parameter = parameters[parameter_name]
                    backups[target] = parameter.detach().clone()
                    source = official_weight(parameter_name)
                    if tuple(source.shape) != tuple(parameter.shape):
                        raise RuntimeError(f"official shape mismatch: {parameter_name}")
                    for row_start in range(0, source.shape[0], args.row_chunk):
                        chunk = source[row_start:row_start + args.row_chunk].to(parameter.dtype)
                        _codes, _scales, _orientations, restored = (
                            recover_full_range_rows_for_storage(
                                torch,
                                chunk,
                                bits=4,
                                group_size=64,
                                scale_format="fp16",
                                scale_search="exhaustive",
                            )
                        )
                        parameter.data[row_start:row_start + restored.shape[0]].copy_(restored)
                    added_code_bytes += int(parameter.numel() * (4 - 2) // 8)
                    del source
                    if index == 1 or index == len(targets) or index % 5 == 0:
                        print(f"[M103] {family} W4 {index}/{len(targets)} {target}", flush=True)
                run = run_once(f"w4_{family}")
                variants[variant_name] = summarize_run(run, targets, added_code_bytes)
                variants[variant_name]["family"] = family
                variants[variant_name]["layers"] = list(target_layers)
                variants[variant_name]["logit_relative_l2_improvement"] = (
                    baseline_logit_relative_l2 - variants[variant_name]["logits"]["relative_l2"]
                )
                variants[variant_name]["logit_relative_l2_improvement_per_MiB"] = (
                    variants[variant_name]["logit_relative_l2_improvement"]
                    / max(added_code_bytes / float(1 << 20), 1.0e-12)
                )
                print(
                    f"[M103] {variant_name} token={variants[variant_name]['generated_token_id']} "
                    f"logit_rel={variants[variant_name]['logits']['relative_l2']:.6f} "
                    f"added_MiB={added_code_bytes / float(1 << 20):.2f}",
                    flush=True,
                )
                del run
            finally:
                with torch.no_grad():
                    for target, backup in backups.items():
                        parameters[f"{target}.weight"].copy_(backup)
                del backups
                gc.collect()

        ranked = sorted(
            (variant_name for variant_name, _family, _layers, _targets in scan_tasks),
            key=lambda variant_name: variants[variant_name]["logit_relative_l2_improvement_per_MiB"],
            reverse=True,
        )
        result.update(
            status="MEASURED_SCREEN_ONLY",
            source_checkpoint={**reload_info, "path": str(args.checkpoint.resolve())},
            prompt_token_count=len(prompt_ids),
            official_bf16_token_id=official_token,
            official_bf16_top5_token_ids=official_top5,
            restored_official_embedding_rows=len(embedding_ids),
            a8_hook_count=len(a8_names),
            activation_policy=args.activation_policy,
            scan_mode=args.scan_mode,
            current_policy={
                "language_layers_0_9": "W2 for q/k/v/o/gate/up/down",
                "language_layers_10_35": "W4 for q/k/v/o/gate/up/down",
                "activation": "A8-G64 FP16-scale-first for language Linear and LM head",
                "lm_head": "current M56 W3 payload (runtime W4 lift does not restore lost precision)",
            },
            w4_proxy=(
                "official BF16 weights requantized with exhaustive full-range W4, group size 64, "
                "FP16 scales; a screening proxy, not an AutoRound-calibrated final artifact"
            ),
            variants=variants,
            benefit_per_storage_ranking=ranked,
            next_gate=(
                "Run per-layer W4 scans inside the best family candidates, include an actual W4 LM-head "
                "and BF16-PS embedding policy, then evaluate Pareto candidates on a frozen multi-case "
                "text/video suite before producing any new board package."
            ),
        )
    except Exception as exc:
        result["error"] = f"{type(exc).__name__}: {exc}"
    finally:
        for handle in reversed(a8_handles):
            handle.remove()
        for handle in reversed(capture_handles):
            handle.remove()
        if auxiliary_npz is not None:
            auxiliary_npz.close()
        result["wall_ms"] = (time.perf_counter() - started) * 1000.0
        atomic_json(args.result, result)
        print(json.dumps(result, ensure_ascii=False), flush=True)
    marker = (
        "M103_MIXED_PRECISION_SENSITIVITY_SCREEN_MEASURED"
        if result["status"] == "MEASURED_SCREEN_ONLY"
        else "M103_MIXED_PRECISION_SENSITIVITY_SCREEN_FAIL"
    )
    print(marker, flush=True)
    return 0 if result["status"] == "MEASURED_SCREEN_ONLY" else 1


if __name__ == "__main__":
    raise SystemExit(main())
