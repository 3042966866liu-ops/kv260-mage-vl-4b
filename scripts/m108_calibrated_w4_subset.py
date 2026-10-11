#!/usr/bin/env python3
"""Calibrate a sensitivity-selected Mage-VL language subset at genuine W4.

This gate starts from the official BF16 checkpoint, not from M56's already
quantized W2 values.  It uses the exact module list selected by the M105 Pareto
screen, runs AutoRound only for that bounded list, and atomically writes a
hash-verified selective cache.  It does not build a board package or mutate the
KV260.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import sys
import time
from pathlib import Path


EXPECTED_RANKING_SHA256 = (
    "b1e1068c04686ca64c02faa5c3359f05622acd386ce5ae5c4e525d84bbb95b9f"
)
EXPECTED_AUTOROUND_COMMIT = "d77c9eaa616bc9f4d8eddad554c9f7b63e59d3a1"


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(8 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def atomic_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + f".tmp-{os.getpid()}")
    temporary.write_text(
        json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    os.replace(temporary, path)


def write_selective_cache(model, targets: list[str], output: Path, policy: dict) -> dict:
    from safetensors.torch import save_file

    output = output.resolve()
    if output.exists():
        raise FileExistsError(f"refusing to overwrite selective cache: {output}")
    output.parent.mkdir(parents=True, exist_ok=True)
    temporary = output.with_name(output.name + f".tmp-{os.getpid()}")
    if temporary.exists():
        shutil.rmtree(temporary)
    temporary.mkdir()
    modules = dict(model.named_modules())
    by_layer: dict[int, list[str]] = {}
    for name in targets:
        layer = int(name.split(".")[3])
        by_layer.setdefault(layer, []).append(name)

    files: list[dict] = []
    try:
        for layer, names in sorted(by_layer.items()):
            tensors = {
                f"{name}.weight": modules[name].weight.detach().cpu().contiguous()
                for name in sorted(names)
            }
            shard = temporary / f"calibrated-w4-layer-{layer:02d}.safetensors"
            save_file(tensors, str(shard))
            files.append(
                {
                    "path": shard.name,
                    "bytes": shard.stat().st_size,
                    "sha256": sha256_file(shard),
                    "tensor_count": len(tensors),
                }
            )
        manifest = {
            "format": "tellme-mage-vl-selective-calibrated-w4-cache-v1",
            "model": "microsoft/Mage-VL",
            "autoround_source_commit": EXPECTED_AUTOROUND_COMMIT,
            "policy": policy,
            "targets": targets,
            "target_count": len(targets),
            "files": files,
            "file_count": len(files),
            "tensor_count": sum(item["tensor_count"] for item in files),
            "total_bytes": sum(item["bytes"] for item in files),
        }
        manifest_path = temporary / "CACHE_MANIFEST.json"
        manifest_path.write_text(
            json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8"
        )
        os.replace(temporary, output)
        manifest["manifest_sha256"] = sha256_file(output / "CACHE_MANIFEST.json")
        return manifest
    except BaseException:
        if temporary.exists():
            shutil.rmtree(temporary)
        raise


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--model", type=Path, required=True)
    parser.add_argument("--autoround", type=Path, required=True)
    parser.add_argument("--deps", type=Path, required=True)
    parser.add_argument("--ranking", type=Path, required=True)
    parser.add_argument(
        "--candidate",
        choices=("top02", "top06", "top15", "early_attention", "mid_kv"),
        default="top15",
    )
    parser.add_argument("--iters", type=int, default=200)
    parser.add_argument("--output-cache", type=Path, required=True)
    parser.add_argument("--result", type=Path, required=True)
    parser.add_argument("--enable-torch-compile", action="store_true")
    args = parser.parse_args()
    if args.iters <= 0:
        parser.error("--iters must be positive")

    result: dict[str, object] = {
        "date": "2026-08-31",
        "gate": "M108-selected-language-calibrated-W4-cache",
        "status": "FAIL",
        "classification": (
            "offline bounded calibration artifact; not a quality PASS, FPGA result, "
            "board package, performance result, video result, or Web result"
        ),
        "candidate": args.candidate,
    }
    started = time.perf_counter()
    try:
        ranking_hash = sha256_file(args.ranking)
        if ranking_hash != EXPECTED_RANKING_SHA256:
            raise RuntimeError(
                f"M105 ranking identity mismatch: {ranking_hash}"
            )
        ranking = json.loads(args.ranking.read_text(encoding="utf-8"))
        if ranking.get("status") != "MEASURED_SCREEN_ONLY":
            raise RuntimeError("M105 ranking is not a measured screen")
        variant = ranking.get("variants", {}).get(args.candidate)
        if args.candidate == "early_attention":
            targets = sorted(
                f"model.language_model.layers.{layer}.self_attn.{suffix}"
                for layer in range(10)
                for suffix in ("q_proj", "k_proj", "v_proj", "o_proj")
            )
        elif args.candidate == "mid_kv":
            targets = sorted(
                f"model.language_model.layers.{layer}.self_attn.{suffix}"
                for layer in range(10, 16)
                for suffix in ("k_proj", "v_proj")
            )
        else:
            if not variant:
                raise RuntimeError(f"candidate missing from ranking: {args.candidate}")
            targets = sorted(str(name) for name in variant["upgraded_modules"])
            if len(targets) != int(variant["upgraded_module_count"]):
                raise RuntimeError("candidate target count mismatch")
        if len(targets) != len(set(targets)):
            raise RuntimeError("candidate contains duplicate targets")
        if not all(
            name.startswith("model.language_model.layers.")
            and (
                (
                    ".mlp." in name
                    and name.endswith(("gate_proj", "up_proj", "down_proj"))
                )
                or (
                    ".self_attn." in name
                    and name.endswith(("q_proj", "k_proj", "v_proj", "o_proj"))
                )
            )
            for name in targets
        ):
            raise RuntimeError("candidate contains a non-approved language MLP target")

        sys.path.insert(0, str(args.deps.resolve()))
        sys.path.insert(0, str(args.autoround.resolve()))
        import torch
        from transformers import AutoModelForCausalLM, AutoProcessor

        import auto_round
        from auto_round import AutoRound
        from auto_round.compressors.mllm.processor import PROCESSORS
        from auto_round.compressors.mllm.template import _register_template

        if not torch.cuda.is_available():
            raise RuntimeError("CUDA is required for M108 calibrated W4")
        if not args.model.is_dir() or not (args.model / "config.json").is_file():
            raise RuntimeError("official model directory is incomplete")

        print(f"[M108] loading official BF16 model; targets={len(targets)}", flush=True)
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
        absent = sorted(set(targets) - set(modules))
        if absent:
            raise RuntimeError(f"selected modules absent from official model: {absent[:3]}")
        for name in targets:
            if not isinstance(modules[name], torch.nn.Linear):
                raise RuntimeError(f"selected target is not Linear: {name}")

        _register_template(
            model_type=str(model.config.model_type),
            default_dataset="local-text-calibration",
            processor=PROCESSORS["hf"],
        )
        calibration = [
            (
                "请用三句话解释 Transformer 中自注意力机制的作用，并说明查询、键和值如何协同。"
                "量化部署时需要同时检查逐层数值误差、最终 token 和语义完整性。"
            ),
            (
                "FPGA edge inference reuses each weight tile across a batch of tokens. "
                "A reliable evaluation compares the same prompts, precision policy, and output limits."
            ),
            (
                "请比较片上缓存与外部 DDR 访存的作用，解释为什么提高权重复用率能够降低首 token 延迟。"
                "回答应当准确、简洁并包含因果关系。"
            ),
            (
                "A language model should answer factual, explanatory, and summarization prompts consistently. "
                "Calibration data therefore covers general language and deployment terminology."
            ),
        ]
        layer_config = {
            name: {
                "bits": 4,
                "group_size": 64,
                "sym": True,
                "data_type": "int",
                "act_bits": 16,
            }
            for name in targets
        }
        policy = {
            "source": "official-BF16-not-M56-W2",
            "ranking_sha256": ranking_hash,
            "candidate": args.candidate,
            "bits": 4,
            "group_size": 64,
            "symmetric": True,
            "iterations": args.iters,
            "samples": len(calibration),
            "sequence_length": 128,
            "targets": targets,
        }
        calibration_started = time.perf_counter()
        compressor = AutoRound(
            model=model,
            tokenizer=processor.tokenizer,
            processor=processor,
            scheme="BF16",
            layer_config=layer_config,
            dataset=calibration,
            iters=args.iters,
            seqlen=128,
            nsamples=len(calibration),
            batch_size=1,
            gradient_accumulate_steps=1,
            low_gpu_mem_usage=True,
            device_map=0,
            enable_torch_compile=args.enable_torch_compile,
            quant_nontext_module=False,
        )
        quantized_model, returned_config = compressor.quantize()
        calibration_ms = (time.perf_counter() - calibration_started) * 1000.0
        missing_returned = sorted(
            name for name in targets if name not in returned_config
        )
        if missing_returned:
            raise RuntimeError(
                f"AutoRound omitted selected targets: {missing_returned[:3]}"
            )
        unexpected_low_bit = sorted(
            name
            for name, config in returned_config.items()
            if int(config.get("bits", 16)) in (2, 3, 4) and name not in targets
        )
        if unexpected_low_bit:
            raise RuntimeError(
                f"AutoRound quantized targets outside M105 selection: {unexpected_low_bit[:3]}"
            )
        quantized_model.to("cpu")
        cache = write_selective_cache(quantized_model, targets, args.output_cache, policy)
        result.update(
            {
                "status": "PASS_CALIBRATED_W4_CACHE_ONLY",
                "autoround_version": auto_round.__version__,
                "autoround_source_commit": EXPECTED_AUTOROUND_COMMIT,
                "cuda_device": torch.cuda.get_device_name(0),
                "ranking_sha256": ranking_hash,
                "target_count": len(targets),
                "targets": targets,
                "calibration_ms": calibration_ms,
                "cache": cache,
                "next_gate": (
                    "Build a genuine official-source W4 LM head, then evaluate top02/top06/top15 "
                    "with BF16 PS embedding on the frozen multi-case text/video quality suite."
                ),
            }
        )
    except BaseException as error:
        result["error"] = f"{type(error).__name__}: {error}"
        result["next_gate"] = "Correct this same offline calibration gate; do not build or stage a board candidate."
    finally:
        result["wall_ms"] = (time.perf_counter() - started) * 1000.0
        atomic_json(args.result, result)

    print(json.dumps(result, indent=2, ensure_ascii=False), flush=True)
    if result["status"] != "PASS_CALIBRATED_W4_CACHE_ONLY":
        return 1
    print("M108_CALIBRATED_W4_CACHE_PASS", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
