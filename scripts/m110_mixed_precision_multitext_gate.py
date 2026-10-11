#!/usr/bin/env python3
"""Measure M56 + calibrated-W4 Pareto candidates on frozen text cases."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import sys
import time
from pathlib import Path


CASES = (
    {
        "name": "factual_capital",
        "prompt": "What is the capital of France? Answer in one short sentence.",
        "semantic_any": (("paris", "巴黎"),),
    },
    {
        "name": "simple_arithmetic",
        "prompt": "计算 17 + 25，只给出结果并用一句话确认。",
        "semantic_any": (("42", "四十二"),),
    },
    {
        "name": "transformer_explanation",
        "prompt": "请用三句话解释Transformer中自注意力机制的作用。",
        "semantic_any": (
            ("自注意力", "self-attention"),
            ("关系", "权重", "attention"),
            ("全局", "依赖", "上下文", "context"),
        ),
    },
    {
        "name": "fpga_weight_reuse",
        "prompt": "请简要解释在FPGA上部署大模型时，提高权重数据复用率为什么能够降低首token延迟。",
        "semantic_any": (
            ("fpga",),
            ("权重", "weight"),
            ("复用", "reuse", "多次使用", "重复使用"),
            ("访存", "带宽", "ddr", "memory", "bandwidth", "数据访问", "传输", "等待", "延迟"),
        ),
    },
)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(8 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def hash_region(path: Path, offset: int, length: int) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        handle.seek(offset)
        remaining = length
        while remaining:
            block = handle.read(min(8 << 20, remaining))
            if not block:
                raise EOFError("artifact ended inside a declared section")
            digest.update(block)
            remaining -= len(block)
    return digest.hexdigest()


def atomic_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + f".tmp-{os.getpid()}")
    temporary.write_text(
        json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    os.replace(temporary, path)


def tensor_metrics(torch, observed, reference) -> dict:
    observed = observed.detach().to(dtype=torch.float64, device="cpu")
    reference = reference.detach().to(dtype=torch.float64, device="cpu")
    if tuple(observed.shape) != tuple(reference.shape):
        raise RuntimeError("metric shape mismatch")
    delta = observed - reference
    ref_norm = max(float(torch.linalg.vector_norm(reference)), 1.0e-12)
    obs_norm = max(float(torch.linalg.vector_norm(observed)), 1.0e-12)
    return {
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


def semantic_contract(answer: str, groups: tuple[tuple[str, ...], ...]) -> dict:
    normalized = answer.casefold()
    matched = [next((term for term in group if term.casefold() in normalized), None) for group in groups]
    return {"passed": all(item is not None for item in matched), "matched": matched}


def load_calibrated_cache_manifest(cache: Path, expected_count: int) -> dict:
    manifest_path = cache / "CACHE_MANIFEST.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if manifest.get("format") != "tellme-mage-vl-selective-calibrated-w4-cache-v1":
        raise RuntimeError("unsupported M108 cache format")
    if (
        manifest.get("target_count") != expected_count
        or manifest.get("tensor_count") != expected_count
    ):
        raise RuntimeError(
            f"M108 cache target-count mismatch: expected={expected_count} "
            f"target_count={manifest.get('target_count')} tensor_count={manifest.get('tensor_count')}"
        )
    for item in manifest["files"]:
        shard = cache / item["path"]
        if shard.stat().st_size != item["bytes"] or sha256_file(shard) != item["sha256"]:
            raise RuntimeError(f"M108 cache shard identity failed: {shard}")
    return manifest


def load_genuine_w4_head(torch, np, model, artifact: Path, helpers) -> dict:
    unpack_orientation_bits, unpack_unsigned_codes, reconstruct = helpers
    manifest_path = artifact / "LM_HEAD_MANIFEST.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if manifest.get("format") != "tellme-mage-vl-genuine-w4-lmhead-v1":
        raise RuntimeError("unsupported M109 LM-head format")
    quant = manifest["quantization"]
    if quant != {
        "bits": 4,
        "group_size": 64,
        "orientation_bit": True,
        "scale_format": "fp16",
        "scale_search": "exhaustive",
        "symmetric_full_range": True,
    }:
        raise RuntimeError("M109 LM-head quantization contract mismatch")
    blob = artifact / manifest["blob"]["path"]
    if blob.stat().st_size != manifest["blob"]["bytes"] or sha256_file(blob) != manifest["blob"]["sha256"]:
        raise RuntimeError("M109 LM-head blob identity failed")
    for section in manifest["blob"]["sections"].values():
        if hash_region(blob, section["offset"], section["bytes"]) != section["sha256"]:
            raise RuntimeError("M109 LM-head section identity failed")

    parameter = dict(model.named_parameters())["lm_head.weight"]
    rows, columns = map(int, parameter.shape)
    groups_per_row = int(manifest["groups_per_row"])
    sections = manifest["blob"]["sections"]
    with blob.open("rb") as handle:
        for row_start in range(0, rows, 32):
            chunk_rows = min(32, rows - row_start)
            code_count = chunk_rows * columns
            code_bytes = code_count * 4 // 8
            scale_bytes = chunk_rows * groups_per_row * 2
            orientation_count = chunk_rows * groups_per_row
            orientation_bytes = math.ceil(orientation_count / 8)
            handle.seek(sections["codes"]["offset"] + row_start * columns * 4 // 8)
            codes = unpack_unsigned_codes(handle.read(code_bytes), 4, code_count)
            handle.seek(sections["scales"]["offset"] + row_start * groups_per_row * 2)
            scales = np.frombuffer(handle.read(scale_bytes), dtype=np.uint16)
            handle.seek(sections["orientations"]["offset"] + row_start * groups_per_row // 8)
            orientations = unpack_orientation_bits(handle.read(orientation_bytes), orientation_count)
            restored = reconstruct(
                torch,
                codes,
                scales,
                orientations,
                bits=4,
                rows=chunk_rows,
                columns=columns,
                group_size=64,
                output_dtype=parameter.dtype,
                scale_format="fp16",
            )
            parameter.data[row_start : row_start + chunk_rows].copy_(restored)
    return {
        "manifest_sha256": sha256_file(manifest_path),
        "blob_sha256": manifest["blob"]["sha256"],
        "blob_bytes": manifest["blob"]["bytes"],
        "roundtrip": manifest["roundtrip"],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--model", type=Path, required=True)
    parser.add_argument("--checkpoint", type=Path, required=True)
    parser.add_argument("--calibrated-cache", type=Path, required=True)
    parser.add_argument("--attention-cache", type=Path)
    parser.add_argument("--mid-kv-cache", type=Path)
    parser.add_argument(
        "--attention-only",
        action="store_true",
        help="Skip already-measured M56/top02/top06 variants and screen top15 plus nested attention candidates.",
    )
    parser.add_argument(
        "--final-only",
        action="store_true",
        help="Apply top15 and only the largest selected Attention set before generation.",
    )
    parser.add_argument(
        "--frozen-checkpoint",
        action="store_true",
        help="Measure the supplied checkpoint exactly as loaded; do not reapply caches or the standalone head.",
    )
    parser.add_argument(
        "--attention-scan",
        choices=("nested_o", "families", "kv_only"),
        default="nested_o",
        help="Choose a nested Attention resource scan so each later point is a strict superset.",
    )
    parser.add_argument(
        "--embedding-mode",
        choices=("bf16", "m56_w3"),
        default="bf16",
        help="Keep the official BF16 embedding or retain M56's packed W3 embedding for a capacity screen.",
    )
    parser.add_argument("--lmhead", type=Path, required=True)
    parser.add_argument("--ranking", type=Path, required=True)
    parser.add_argument("--deps", type=Path, required=True)
    parser.add_argument("--result", type=Path, required=True)
    parser.add_argument("--new-tokens", type=int, default=24)
    parser.add_argument(
        "--case",
        action="append",
        choices=tuple(case["name"] for case in CASES),
        help="Run only selected frozen cases; repeat for more than one.",
    )
    parser.add_argument("--threads", type=int, default=20)
    args = parser.parse_args()
    if args.new_tokens <= 0:
        parser.error("--new-tokens must be positive")
    if args.attention_only and not args.attention_cache:
        parser.error("--attention-only requires --attention-cache")
    if args.final_only and not args.attention_only:
        parser.error("--final-only requires --attention-only")

    result: dict[str, object] = {
        "date": "2026-08-31",
        "gate": (
            "M112-mixed-precision-attention-resource-quality-measurement"
            if args.attention_cache
            else "M110-mixed-precision-frozen-multitext-quality-measurement"
        ),
        "status": "FAIL",
        "classification": (
            "offline multi-case quality measurement; no threshold is inferred here and it is not "
            "an FPGA result, board package, performance result, video result, or Web result"
        ),
    }
    started = time.perf_counter()
    a8_handles = []
    layer_handles = []
    try:
        sys.path.insert(0, str(args.deps.resolve()))
        sys.path.insert(0, str((Path(__file__).resolve().parents[1] / "deployment" / "mage_vl4b" / "scripts").resolve()))
        import numpy as np
        import torch
        from safetensors import safe_open
        from transformers import AutoModelForCausalLM, AutoProcessor

        from mage_a8_runtime import install_packed_linear_a8_hooks
        from mixed_bit_checkpoint import (
            reconstruct_full_range_rows_from_storage,
            recover_full_range_rows_for_storage,
            unpack_orientation_bits,
            unpack_unsigned_codes,
        )
        from packed_checkpoint_artifact import load_packed_checkpoint

        torch.set_num_threads(args.threads)
        ranking = json.loads(args.ranking.read_text(encoding="utf-8"))
        variants = ranking["variants"]
        sets = {
            name: set(variants[name]["upgraded_modules"])
            for name in ("top02", "top06", "top15")
        }
        if not sets["top02"] < sets["top06"] < sets["top15"]:
            raise RuntimeError("M105 Pareto target sets are not strictly nested")
        cache = args.calibrated_cache.resolve()
        cache_manifest = load_calibrated_cache_manifest(cache, 22)
        if set(cache_manifest["targets"]) != sets["top15"]:
            raise RuntimeError("M108 target set does not equal M105 top15")
        attention_cache = args.attention_cache.resolve() if args.attention_cache else None
        attention_manifest = None
        mid_kv_cache = args.mid_kv_cache.resolve() if args.mid_kv_cache else None
        mid_kv_manifest = None
        attention_sets: dict[str, set[str]] = {}
        if attention_cache:
            attention_manifest = load_calibrated_cache_manifest(attention_cache, 40)
            expected_attention = {
                f"model.language_model.layers.{layer}.self_attn.{family}_proj"
                for layer in range(10)
                for family in ("q", "k", "v", "o")
            }
            if set(attention_manifest["targets"]) != expected_attention:
                raise RuntimeError("M111 target set is not the locked layer0-9 Q/K/V/O set")
            if args.attention_scan == "nested_o":
                attention_sets = {
                    "top15_plus_layer0_o": {
                        "model.language_model.layers.0.self_attn.o_proj"
                    },
                    "top15_plus_early_o": {
                        f"model.language_model.layers.{layer}.self_attn.o_proj"
                        for layer in range(10)
                    },
                    "top15_plus_early_attention": expected_attention,
                }
            elif args.attention_scan == "families":
                attention_sets = {
                    "top15_plus_early_kv": {
                        f"model.language_model.layers.{layer}.self_attn.{family}_proj"
                        for layer in range(10)
                        for family in ("k", "v")
                    },
                    "top15_plus_early_qkv": {
                        f"model.language_model.layers.{layer}.self_attn.{family}_proj"
                        for layer in range(10)
                        for family in ("q", "k", "v")
                    },
                    "top15_plus_early_attention": expected_attention,
                }
            else:
                attention_sets = {
                    "top15_plus_early_kv": {
                        f"model.language_model.layers.{layer}.self_attn.{family}_proj"
                        for layer in range(10)
                        for family in ("k", "v")
                    }
                }
                if mid_kv_cache:
                    mid_kv_manifest = load_calibrated_cache_manifest(mid_kv_cache, 12)
                    expected_mid_kv = {
                        f"model.language_model.layers.{layer}.self_attn.{family}_proj"
                        for layer in range(10, 16)
                        for family in ("k", "v")
                    }
                    if set(mid_kv_manifest["targets"]) != expected_mid_kv:
                        raise RuntimeError("M115 target set is not the locked layer10-15 K/V set")
                    attention_sets["top15_plus_kv_layer00_15"] = (
                        attention_sets["top15_plus_early_kv"] | expected_mid_kv
                    )

        print("[M110] loading official BF16 model", flush=True)
        processor = AutoProcessor.from_pretrained(
            args.model, trust_remote_code=True, local_files_only=True
        )
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
        captured_layers: dict[str, object] = {}
        capture_enabled = False

        def make_hook(name: str):
            def hook(_module, _inputs, output):
                if not capture_enabled:
                    return
                value = output[0] if isinstance(output, (tuple, list)) else output
                captured_layers[name] = value.detach()[0, -1].float().cpu().contiguous()
            return hook

        for layer in range(36):
            name = f"model.language_model.layers.{layer}"
            layer_handles.append(modules[name].register_forward_hook(make_hook(f"layer{layer:02d}")))

        prepared_cases = []
        selected_cases = tuple(
            case for case in CASES if not args.case or case["name"] in args.case
        )
        for case in selected_cases:
            rendered = processor.apply_chat_template(
                [{"role": "user", "content": [{"type": "text", "text": case["prompt"]}]}],
                tokenize=False,
                add_generation_prompt=True,
            )
            inputs = processor(text=[rendered], return_tensors="pt", padding=True)
            prepared_cases.append((case, inputs))

        def run_variant(label: str) -> dict:
            cases = []
            for case, inputs in prepared_cases:
                captured_layers.clear()
                nonlocal capture_enabled
                capture_enabled = True
                run_started = time.perf_counter()
                with torch.inference_mode():
                    prefill = model(**inputs, use_cache=False, return_dict=True)
                capture_enabled = False
                logits = prefill.logits[0, -1].float().cpu()
                layers = {name: value.clone() for name, value in captured_layers.items()}
                if len(layers) != 36:
                    raise RuntimeError(f"{label}/{case['name']}: incomplete layer capture")
                with torch.inference_mode():
                    output = model.generate(
                        **inputs,
                        max_new_tokens=args.new_tokens,
                        min_new_tokens=args.new_tokens,
                        do_sample=False,
                        use_cache=True,
                    )
                new_ids = output[0, inputs["input_ids"].shape[1] :].cpu().tolist()
                answer = processor.tokenizer.decode(new_ids, skip_special_tokens=True)
                cases.append(
                    {
                        "name": case["name"],
                        "prompt": case["prompt"],
                        "prompt_token_count": int(inputs["input_ids"].shape[1]),
                        "logits": logits,
                        "top5": [int(value) for value in torch.topk(logits, 5).indices],
                        "layers": layers,
                        "generated_token_ids": [int(value) for value in new_ids],
                        "answer": answer,
                        "semantic_contract": semantic_contract(answer, case["semantic_any"]),
                        "elapsed_ms": (time.perf_counter() - run_started) * 1000.0,
                    }
                )
                print(
                    f"[M110/M112] {label}/{case['name']} token0={new_ids[0]} "
                    f"semantic={cases[-1]['semantic_contract']['passed']}",
                    flush=True,
                )
            return {"label": label, "cases": cases}

        official = run_variant("official_bf16")
        official_embedding = model.get_input_embeddings().weight.detach().clone()

        print("[M110] loading exact M56 checkpoint", flush=True)
        m56_info = load_packed_checkpoint(torch, model, args.checkpoint, verify_blob=True, row_chunk=32)
        if args.embedding_mode == "bf16" and not args.frozen_checkpoint:
            model.get_input_embeddings().weight.data.copy_(official_embedding)
        del official_embedding
        lmhead_info = (
            {"source": "supplied-frozen-checkpoint"}
            if args.frozen_checkpoint
            else load_genuine_w4_head(
                torch,
                np,
                model,
                args.lmhead.resolve(),
                (unpack_orientation_bits, unpack_unsigned_codes, reconstruct_full_range_rows_from_storage),
            )
        )
        a8_handles, a8_names = install_packed_linear_a8_hooks(
            torch,
            model,
            args.checkpoint,
            r"^(model\.language_model\.layers\.|lm_head$)",
        )

        cache_index: dict[str, tuple[Path, str]] = {}
        for item in cache_manifest["files"]:
            shard = cache / item["path"]
            with safe_open(str(shard), framework="pt", device="cpu") as handle:
                for tensor_name in handle.keys():
                    cache_index[tensor_name.removesuffix(".weight")] = (shard, tensor_name)
        if attention_cache and attention_manifest:
            for item in attention_manifest["files"]:
                shard = attention_cache / item["path"]
                with safe_open(str(shard), framework="pt", device="cpu") as handle:
                    for tensor_name in handle.keys():
                        name = tensor_name.removesuffix(".weight")
                        if name in cache_index:
                            raise RuntimeError(f"overlapping calibrated caches: {name}")
                        cache_index[name] = (shard, tensor_name)
        if mid_kv_cache and mid_kv_manifest:
            for item in mid_kv_manifest["files"]:
                shard = mid_kv_cache / item["path"]
                with safe_open(str(shard), framework="pt", device="cpu") as handle:
                    for tensor_name in handle.keys():
                        name = tensor_name.removesuffix(".weight")
                        if name in cache_index:
                            raise RuntimeError(f"overlapping calibrated caches: {name}")
                        cache_index[name] = (shard, tensor_name)

        applied: set[str] = set()
        storage_stats: dict[str, dict] = {}

        def apply_targets(targets: set[str]) -> None:
            for name in sorted(targets - applied):
                shard, tensor_name = cache_index[name]
                with safe_open(str(shard), framework="pt", device="cpu") as handle:
                    calibrated = handle.get_tensor(tensor_name)
                parameter = modules[name].weight
                if tuple(calibrated.shape) != tuple(parameter.shape):
                    raise RuntimeError(f"M108 target shape mismatch: {name}")
                error_squared = source_squared = 0.0
                max_abs = 0.0
                for row_start in range(0, calibrated.shape[0], 32):
                    source = calibrated[row_start : row_start + 32].to(parameter.dtype)
                    _codes, _scales, _orientations, restored = recover_full_range_rows_for_storage(
                        torch,
                        source,
                        bits=4,
                        group_size=64,
                        scale_format="fp16",
                        scale_search="exhaustive",
                    )
                    delta = restored.float() - source.float()
                    error_squared += float(torch.sum(delta * delta))
                    source_squared += float(torch.sum(source.float() ** 2))
                    max_abs = max(max_abs, float(torch.max(torch.abs(delta))))
                    parameter.data[row_start : row_start + restored.shape[0]].copy_(restored)
                storage_stats[name] = {
                    "relative_l2_to_calibrated_weight": math.sqrt(error_squared / source_squared),
                    "max_abs_to_calibrated_weight": max_abs,
                    "code_bytes": int(parameter.numel() * 4 // 8),
                    "incremental_bytes_over_w2": int(parameter.numel() * (4 - 2) // 8),
                }
                applied.add(name)

        measured = {}
        if args.frozen_checkpoint:
            measured["frozen_checkpoint"] = run_variant("frozen_checkpoint")
        elif args.final_only:
            apply_targets(sets["top15"])
            final_name = next(reversed(attention_sets))
            apply_targets(attention_sets[final_name])
            measured[final_name] = run_variant(final_name)
        else:
            if not args.attention_only:
                measured["baseline_m56_w4head"] = run_variant("baseline_m56_w4head")
            for name in (("top15",) if args.attention_only else ("top02", "top06", "top15")):
                apply_targets(sets[name])
                measured[name] = run_variant(name)
            for name in attention_sets:
                apply_targets(attention_sets[name])
                measured[name] = run_variant(name)

        official_by_name = {case["name"]: case for case in official["cases"]}

        def summarize(variant: dict) -> dict:
            cases = []
            for observed in variant["cases"]:
                reference = official_by_name[observed["name"]]
                generated = observed["generated_token_ids"]
                expected = reference["generated_token_ids"]
                prefix = 0
                for left, right in zip(generated, expected):
                    if left != right:
                        break
                    prefix += 1
                layer_metrics = {
                    name: tensor_metrics(torch, observed["layers"][name], reference["layers"][name])
                    for name in sorted(reference["layers"])
                }
                cases.append(
                    {
                        "name": observed["name"],
                        "prompt": observed["prompt"],
                        "prompt_token_count": observed["prompt_token_count"],
                        "official_token_ids": expected,
                        "generated_token_ids": generated,
                        "official_answer": reference["answer"],
                        "generated_answer": observed["answer"],
                        "exact_sequence_match": generated == expected,
                        "token_agreement_fraction": sum(a == b for a, b in zip(generated, expected)) / len(expected),
                        "exact_prefix_tokens": prefix,
                        "first_token_match": generated[0] == expected[0],
                        "top1_in_official_top5": generated[0] in reference["top5"],
                        "top5_overlap_count": len(set(observed["top5"]) & set(reference["top5"])),
                        "semantic_contract": observed["semantic_contract"],
                        "official_semantic_contract": reference["semantic_contract"],
                        "logits": tensor_metrics(torch, observed["logits"], reference["logits"]),
                        "layer_metrics": layer_metrics,
                        "max_layer_relative_l2": max(item["relative_l2"] for item in layer_metrics.values()),
                        "min_layer_cosine": min(item["cosine"] for item in layer_metrics.values()),
                        "elapsed_ms": observed["elapsed_ms"],
                    }
                )
            return {
                "cases": cases,
                "case_count": len(cases),
                "all_finite": all(
                    case["logits"]["finite"]
                    and all(item["finite"] for item in case["layer_metrics"].values())
                    for case in cases
                ),
                "first_token_matches": sum(case["first_token_match"] for case in cases),
                "exact_sequence_matches": sum(case["exact_sequence_match"] for case in cases),
                "semantic_passes": sum(case["semantic_contract"]["passed"] for case in cases),
                "mean_token_agreement_fraction": sum(case["token_agreement_fraction"] for case in cases) / len(cases),
                "mean_logit_relative_l2": sum(case["logits"]["relative_l2"] for case in cases) / len(cases),
                "mean_logit_cosine": sum(case["logits"]["cosine"] for case in cases) / len(cases),
            }

        official_summary = {
            "cases": [
                {
                    "name": case["name"],
                    "prompt": case["prompt"],
                    "prompt_token_count": case["prompt_token_count"],
                    "generated_token_ids": case["generated_token_ids"],
                    "answer": case["answer"],
                    "top5": case["top5"],
                    "semantic_contract": case["semantic_contract"],
                    "elapsed_ms": case["elapsed_ms"],
                }
                for case in official["cases"]
            ]
        }
        summarized = {name: summarize(value) for name, value in measured.items()}
        result.update(
            {
                "status": "MEASURED_NO_ACCEPTANCE_INFERRED",
                "new_tokens": args.new_tokens,
                "selected_cases": [case["name"] for case in selected_cases],
                "official": official_summary,
                "variants": summarized,
                "m56": m56_info,
                "embedding_mode": args.embedding_mode,
                "bf16_ps_embedding": args.embedding_mode == "bf16",
                "genuine_w4_lmhead": lmhead_info,
                "a8_hook_count": len(a8_names),
                "calibrated_cache": {
                    "manifest_sha256": sha256_file(cache / "CACHE_MANIFEST.json"),
                    "target_count": cache_manifest["target_count"],
                    "storage_roundtrip": storage_stats,
                },
                "attention_cache": (
                    {
                        "manifest_sha256": sha256_file(attention_cache / "CACHE_MANIFEST.json"),
                        "target_count": attention_manifest["target_count"],
                        "nested_variant_incremental_bytes_over_w2": {
                            name: sum(
                                int(modules[target].weight.numel() * (4 - 2) // 8)
                                for target in targets
                            )
                            for name, targets in attention_sets.items()
                        },
                    }
                    if attention_cache and attention_manifest
                    else None
                ),
                "mid_kv_cache": (
                    {
                        "manifest_sha256": sha256_file(mid_kv_cache / "CACHE_MANIFEST.json"),
                        "target_count": mid_kv_manifest["target_count"],
                    }
                    if mid_kv_cache and mid_kv_manifest
                    else None
                ),
                "next_gate": (
                    "Review all four frozen text cases without inferring success from one prompt, "
                    "then run the retained three-case video suite for the non-dominated candidate(s)."
                ),
            }
        )
    except BaseException as error:
        result["error"] = f"{type(error).__name__}: {error}"
        result["next_gate"] = "Correct this same offline text-quality gate; do not build or stage a board candidate."
    finally:
        for handle in a8_handles + layer_handles:
            handle.remove()
        result["wall_ms"] = (time.perf_counter() - started) * 1000.0
        atomic_json(args.result, result)

    print(json.dumps(result, indent=2, ensure_ascii=False), flush=True)
    if result["status"] != "MEASURED_NO_ACCEPTANCE_INFERRED":
        return 1
    print("M110_M112_MULTITEXT_MEASUREMENT_COMPLETE", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
