#!/usr/bin/env python3
"""Capture the exact M120+A8 fixed-text family-boundary golden in a fresh process."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
import time
from pathlib import Path


EXPECTED_MANIFEST_SHA256 = "5ff33d1922376e18277902a8b051d069315f79c11b4f63e8d72517acd1dcd5d0"
EXPECTED_BLOB_SHA256 = "9c7de8995a08602186c7090081bbfc10b7c51170ad7e544f2f2dc71333b4f21d"
LAYERS = 36
BASE_FAMILIES = {
    "qkv": "self_attn.q_proj",
    "attention_out": "self_attn.o_proj",
    "gate_up": "mlp.gate_proj",
    "mlp_down": "mlp.down_proj",
}


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(16 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def atomic_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + f".tmp-{os.getpid()}")
    temporary.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    os.replace(temporary, path)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--model", type=Path, required=True)
    parser.add_argument("--checkpoint", type=Path, required=True)
    parser.add_argument("--reference", type=Path, required=True)
    parser.add_argument("--capture-output", type=Path, required=True)
    parser.add_argument("--result", type=Path, required=True)
    parser.add_argument("--threads", type=int, default=20)
    args = parser.parse_args()

    repo = Path(__file__).resolve().parents[1]
    sys.path.insert(0, str(repo / "deployment" / "mage_vl4b" / "scripts"))
    import numpy as np
    import torch
    from transformers import AutoModelForCausalLM

    from mage_a8_runtime import install_packed_linear_a8_hooks
    from packed_checkpoint_artifact import load_packed_checkpoint

    torch.set_num_threads(args.threads)
    result: dict[str, object] = {
        "date": "2026-08-31",
        "gate": "M127-M120-same-quantized-fixed-text-family-golden",
        "status": "FAIL",
        "classification": "fresh-process offline M120+A8 software golden; not CSim, CoSim, FPGA, board, performance or Web evidence",
    }
    started = time.perf_counter()
    capture_handles = []
    a8_handles = []
    try:
        checkpoint = args.checkpoint.resolve()
        manifest_path = checkpoint / "CHECKPOINT_MANIFEST.json"
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        if sha256_file(manifest_path) != EXPECTED_MANIFEST_SHA256:
            raise RuntimeError("M127_MANIFEST_IDENTITY_FAIL")
        if manifest["blob"]["sha256"] != EXPECTED_BLOB_SHA256:
            raise RuntimeError("M127_BLOB_DECLARATION_FAIL")

        reference = json.loads(args.reference.read_text(encoding="utf-8"))
        prompt_ids = [int(value) for value in reference["prompt_token_ids"]]
        if len(prompt_ids) != 30:
            raise RuntimeError("M127_FIXED_PROMPT_LENGTH_FAIL")

        print("[M127] loading official model shell", flush=True)
        model = AutoModelForCausalLM.from_pretrained(
            args.model,
            trust_remote_code=True,
            local_files_only=True,
            torch_dtype=torch.bfloat16,
            low_cpu_mem_usage=True,
            attn_implementation="eager",
            device_map={"": "cpu"},
        ).eval()
        print("[M127] loading and hash-verifying exact M120 checkpoint", flush=True)
        reload_info = load_packed_checkpoint(
            torch, model, checkpoint, verify_blob=True, row_chunk=32
        )
        if reload_info["manifest_sha256"] != EXPECTED_MANIFEST_SHA256:
            raise RuntimeError("M127_RELOAD_MANIFEST_IDENTITY_FAIL")
        if reload_info["blob_sha256"] != EXPECTED_BLOB_SHA256:
            raise RuntimeError("M127_RELOAD_BLOB_IDENTITY_FAIL")

        modules = dict(model.named_modules())
        requested: dict[str, str] = {}
        for layer in range(LAYERS):
            for family, suffix in BASE_FAMILIES.items():
                logical = f"layer{layer:02d}_{family}"
                expected = f"model.language_model.layers.{layer}.{suffix}"
                if expected in modules:
                    requested[logical] = expected
                    continue
                matches = [name for name in modules if name.endswith(f"language_model.layers.{layer}.{suffix}")]
                if len(matches) != 1:
                    raise RuntimeError(f"M127_TARGET_DISCOVERY_FAIL logical={logical} matches={matches}")
                requested[logical] = matches[0]

        captured: dict[str, object] = {}

        def make_hook(logical: str):
            def hook(_module, positional):
                if logical in captured:
                    raise RuntimeError(f"M127_DUPLICATE_CAPTURE logical={logical}")
                if not positional or not torch.is_tensor(positional[0]):
                    raise RuntimeError(f"M127_INVALID_CAPTURE logical={logical}")
                value = positional[0].detach().to(dtype=torch.float32, device="cpu")
                if value.ndim != 3 or value.shape[0] != 1:
                    raise RuntimeError(f"M127_CAPTURE_GEOMETRY_FAIL logical={logical} shape={tuple(value.shape)}")
                captured[logical] = value[0].contiguous()
            return hook

        for logical, actual in requested.items():
            capture_handles.append(modules[actual].register_forward_pre_hook(make_hook(logical)))
        a8_handles, a8_names = install_packed_linear_a8_hooks(
            torch, model, checkpoint, r"^(model\.language_model\.layers\.|lm_head$)"
        )
        if len(a8_names) != 253:
            raise RuntimeError(f"M127_A8_HOOK_CLOSURE_FAIL count={len(a8_names)}")

        input_ids = torch.tensor([prompt_ids], dtype=torch.long)
        attention_mask = torch.ones_like(input_ids)
        print("[M127] running one exact 30-token M120+A8 prefill", flush=True)
        with torch.inference_mode():
            outputs = model(
                input_ids=input_ids,
                attention_mask=attention_mask,
                use_cache=False,
                return_dict=True,
            )
        logits = outputs.logits[0, -1].to(dtype=torch.float32, device="cpu").contiguous()
        generated_token = int(torch.argmax(logits))
        if len(captured) != 144:
            raise RuntimeError(f"M127_BASE_CAPTURE_CLOSURE_FAIL count={len(captured)}")
        if not torch.isfinite(logits).all() or not all(torch.isfinite(value).all() for value in captured.values()):
            raise RuntimeError("M127_NONFINITE_GOLDEN")

        emitted: dict[str, object] = {}
        for layer in range(LAYERS):
            base = captured[f"layer{layer:02d}_qkv"]
            if layer < 10:
                emitted[f"layer{layer:02d}_q"] = base
                emitted[f"layer{layer:02d}_kv"] = base.clone()
            else:
                emitted[f"layer{layer:02d}_qkv"] = base
            for family in ("attention_out", "gate_up", "mlp_down"):
                emitted[f"layer{layer:02d}_{family}"] = captured[f"layer{layer:02d}_{family}"]
        if len(emitted) != 154:
            raise RuntimeError(f"M127_EMITTED_CHAIN_CLOSURE_FAIL count={len(emitted)}")

        args.capture_output.parent.mkdir(parents=True, exist_ok=True)
        temporary = args.capture_output.with_suffix(args.capture_output.suffix + f".tmp-{os.getpid()}")
        arrays = {
            name: value.numpy().astype(np.float32, copy=False)
            for name, value in sorted(emitted.items())
        }
        arrays["final_logits"] = logits.numpy().astype(np.float32, copy=False)
        with temporary.open("wb") as handle:
            np.savez(handle, **arrays)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, args.capture_output)

        sketches = {}
        for name, value in sorted(emitted.items()):
            array = value.numpy().astype(np.float32, copy=False)
            flat = array.reshape(-1)
            step = max(1, flat.size // 512)
            sample = flat[::step][:512]
            sketches[name] = {
                "shape": list(array.shape),
                "finite": bool(np.isfinite(array).all()),
                "minimum": float(array.min()),
                "maximum": float(array.max()),
                "l2": float(np.linalg.norm(array.astype(np.float64))),
                "sample_stride": step,
                "sample_sha256_fp32": hashlib.sha256(sample.astype("<f4").tobytes()).hexdigest(),
            }

        result.update(
            {
                "status": "PASS_M120_SAME_QUANTIZED_154_CHAIN_GOLDEN",
                "source_checkpoint": {**reload_info, "path": str(checkpoint)},
                "prompt_token_count": len(prompt_ids),
                "official_bf16_token_id": int(reference["generated_token_ids"][0]),
                "m120_a8_token_id": generated_token,
                "a8_hook_count": len(a8_names),
                "base_capture_count": len(captured),
                "emitted_chain_input_count": len(emitted),
                "split_q_kv_layers": list(range(10)),
                "all_finite": True,
                "capture_output": str(args.capture_output.resolve()),
                "capture_output_bytes": args.capture_output.stat().st_size,
                "capture_output_sha256": sha256_file(args.capture_output),
                "final_logits_sha256_fp32": hashlib.sha256(logits.numpy().astype("<f4").tobytes()).hexdigest(),
                "sketches": sketches,
                "board_state_changed": False,
                "stable_rollback_preserved": True,
                "next_gate": "Use these exact chain inputs to build the M120 real-record numerical CSim fixture; no board work before CSim and RTL CoSim pass.",
            }
        )
    except BaseException as error:
        result["error"] = f"{type(error).__name__}: {error}"
        result["next_gate"] = "Correct this same fresh-process golden gate; do not touch the board."
    finally:
        for handle in reversed(a8_handles):
            handle.remove()
        for handle in reversed(capture_handles):
            handle.remove()
        result["wall_ms"] = (time.perf_counter() - started) * 1000.0
        atomic_json(args.result, result)
        print(json.dumps({key: value for key, value in result.items() if key != "sketches"}, ensure_ascii=False), flush=True)

    if result["status"] != "PASS_M120_SAME_QUANTIZED_154_CHAIN_GOLDEN":
        print("M127_M120_SAME_QUANTIZED_GOLDEN_FAIL", flush=True)
        return 1
    print("M127_M120_SAME_QUANTIZED_GOLDEN_PASS", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
