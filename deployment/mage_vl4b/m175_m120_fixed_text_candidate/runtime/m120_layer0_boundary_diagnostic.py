#!/usr/bin/env python3
"""Measure complete M120 Layer-0 propagation against accepted M127 boundaries."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
import time
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from board_runtime import M120BoardRuntime
from text_e2e_gate import HEADS, HEAD_DIM, KV_HEADS, apply_rope, attention, rms_norm, silu


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(8 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def metrics(actual: np.ndarray, reference: np.ndarray) -> dict:
    lhs = np.asarray(actual, dtype=np.float32)
    rhs = np.asarray(reference, dtype=np.float32)
    if lhs.shape != rhs.shape:
        raise RuntimeError(f"boundary shape mismatch {lhs.shape} != {rhs.shape}")
    finite = bool(np.isfinite(lhs).all() and np.isfinite(rhs).all())
    if not finite:
        return {"shape": list(lhs.shape), "finite": False}
    delta = lhs.astype(np.float64) - rhs.astype(np.float64)
    lhs64, rhs64 = lhs.astype(np.float64), rhs.astype(np.float64)
    lhs_norm = float(np.linalg.norm(lhs64))
    rhs_norm = float(np.linalg.norm(rhs64))
    return {
        "shape": list(lhs.shape),
        "finite": True,
        "max_abs": float(np.max(np.abs(delta))),
        "mean_abs": float(np.mean(np.abs(delta))),
        "rmse": float(np.sqrt(np.mean(np.square(delta)))),
        "relative_l2": float(np.linalg.norm(delta) / max(rhs_norm, 1.0e-30)),
        "cosine": float(np.vdot(lhs64.ravel(), rhs64.ravel()) / max(lhs_norm * rhs_norm, 1.0e-30)),
        "actual_sha256_fp32": hashlib.sha256(lhs.astype("<f4", copy=False).tobytes()).hexdigest(),
        "reference_sha256_fp32": hashlib.sha256(rhs.astype("<f4", copy=False).tobytes()).hexdigest(),
    }


def atomic_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + f".tmp-{os.getpid()}")
    temporary.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    os.replace(temporary, path)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--overlay", type=Path, required=True)
    parser.add_argument("--language", type=Path, required=True)
    parser.add_argument("--head", type=Path, required=True)
    parser.add_argument("--language-contract", type=Path, required=True)
    parser.add_argument("--head-contract", type=Path, required=True)
    parser.add_argument("--auxiliary", type=Path, required=True)
    parser.add_argument("--auxiliary-manifest", type=Path, required=True)
    parser.add_argument("--reference", type=Path, required=True)
    parser.add_argument("--boundaries", type=Path, required=True)
    parser.add_argument("--boundaries-result", type=Path, required=True)
    parser.add_argument("--result", type=Path, required=True)
    parser.add_argument(
        "--weight-mode", choices=("resident-high-ddr", "staged-low-cma"), default="staged-low-cma"
    )
    args = parser.parse_args()
    started = time.monotonic()
    result = {
        "date": "2026-09-01",
        "gate": "M144-M120-complete-layer0-boundary-diagnostic",
        "status": "FAIL",
        "classification": "real-board Layer-0 diagnostic; thresholds are applied by a separate predeclared acceptance gate",
    }
    runtime = None
    aux_archive = None
    boundary_archive = None
    try:
        boundary_result = json.loads(args.boundaries_result.read_text(encoding="utf-8"))
        if boundary_result.get("status") != "PASS":
            raise RuntimeError("M143 boundary result status mismatch")
        if boundary_result.get("fixture_sha256") != sha256(args.boundaries):
            raise RuntimeError("M143 boundary fixture identity mismatch")
        boundary_archive = np.load(args.boundaries, allow_pickle=False)
        boundary = {name: np.asarray(boundary_archive[name], dtype=np.float32) for name in boundary_archive.files}

        reference = json.loads(args.reference.read_text(encoding="utf-8"))
        token_ids = [int(value) for value in reference["prompt_token_ids"]]
        if len(token_ids) != 30:
            raise RuntimeError("only the frozen 30-token reference is accepted")
        aux_manifest = json.loads(args.auxiliary_manifest.read_text(encoding="utf-8"))
        if aux_manifest.get("result") != "PASS" or aux_manifest.get("payload_sha256") != sha256(args.auxiliary):
            raise RuntimeError("auxiliary identity mismatch")
        aux_archive = np.load(args.auxiliary, allow_pickle=False)
        auxiliary = {name: np.asarray(aux_archive[name], dtype=np.float32) for name in aux_archive.files}
        selected_ids = [int(value) for value in aux_manifest["selected_embedding_ids"]]
        embedding_rows = auxiliary["model.language_model.embed_tokens.weight"]
        embedding = {token: embedding_rows[index] for index, token in enumerate(selected_ids)}
        hidden = np.stack([embedding[token] for token in token_ids]).astype(np.float32)

        runtime = M120BoardRuntime(
            args.overlay,
            args.language,
            args.head,
            args.language_contract,
            args.head_contract,
            weight_mode=args.weight_mode,
        )
        prefix = "model.language_model.layers.0"
        measured = {}

        residual = hidden
        normed = rms_norm(hidden, auxiliary[f"{prefix}.input_layernorm.weight"])
        measured["layer00_q_input"] = metrics(normed, boundary["layer00_q"])
        measured["layer00_kv_input"] = metrics(normed, boundary["layer00_kv"])
        q_out = runtime.language_family(0, "q", normed)
        kv_out = runtime.language_family(0, "kv", normed)
        query = q_out[f"{prefix}.self_attn.q_proj"][:30].reshape(-1, HEADS, HEAD_DIM)
        key = kv_out[f"{prefix}.self_attn.k_proj"][:30].reshape(-1, KV_HEADS, HEAD_DIM)
        value = kv_out[f"{prefix}.self_attn.v_proj"][:30].reshape(-1, KV_HEADS, HEAD_DIM)
        query = rms_norm(query, auxiliary[f"{prefix}.self_attn.q_norm.weight"])
        key = rms_norm(key, auxiliary[f"{prefix}.self_attn.k_norm.weight"])
        query, key = apply_rope(query, key)
        attention_input = attention(query, key, value)
        measured["layer00_attention_out_input"] = metrics(
            attention_input, boundary["layer00_attention_out"]
        )

        projected = runtime.language_family(0, "attention_out", attention_input)
        hidden = residual + projected[f"{prefix}.self_attn.o_proj"][:30]
        residual = hidden
        normed = rms_norm(hidden, auxiliary[f"{prefix}.post_attention_layernorm.weight"])
        measured["layer00_gate_up_input"] = metrics(normed, boundary["layer00_gate_up"])

        gate_up = runtime.language_family(0, "gate_up", normed)
        gate = gate_up[f"{prefix}.mlp.gate_proj"][:30]
        up = gate_up[f"{prefix}.mlp.up_proj"][:30]
        mlp_input = silu(gate) * up
        measured["layer00_mlp_down_input"] = metrics(mlp_input, boundary["layer00_mlp_down"])

        down = runtime.language_family(0, "mlp_down", mlp_input)
        hidden = residual + down[f"{prefix}.mlp.down_proj"][:30]
        layer1_input = rms_norm(
            hidden, auxiliary["model.language_model.layers.1.input_layernorm.weight"]
        )
        measured["layer01_q_input"] = metrics(layer1_input, boundary["layer01_q"])
        measured["layer01_kv_input"] = metrics(layer1_input, boundary["layer01_kv"])

        evidence = runtime.evidence()
        layer0_chains = [
            chain for chain in runtime.language_contract.chains if int(chain["layer"]) == 0
        ]
        expected_macros = sum(int(chain["expected_macros"]) for chain in layer0_chains)
        hardware_ok = (
            len(layer0_chains) == 5
            and evidence.get("logical_calls") == 5
            and evidence.get("logical_expected_macros") == expected_macros
            and int(evidence.get("host_calls", -1)) >= 5
            and int(evidence.get("expected_macros", -1)) >= expected_macros
        )
        result.update(
            {
                "status": "MEASURED" if hardware_ok else "FAIL",
                "build_id": evidence.get("build_id"),
                "fpga_execution_proved": hardware_ok,
                "expected_logical_calls": 5,
                "expected_macros": expected_macros,
                "evidence": evidence,
                "metrics": measured,
                "all_boundaries_finite": all(item.get("finite") is True for item in measured.values()),
                "total_ms": (time.monotonic() - started) * 1000.0,
                "next_gate": "Apply the predeclared M144 Layer-0 boundary acceptance gate; fixed-text remains locked until it passes.",
            }
        )
    except BaseException as error:
        result["error"] = f"{type(error).__name__}: {error}"
        result["total_ms"] = (time.monotonic() - started) * 1000.0
        result["next_gate"] = "Debug and rerun complete Layer-0 only."
    finally:
        if runtime is not None:
            runtime.close()
        if aux_archive is not None:
            aux_archive.close()
        if boundary_archive is not None:
            boundary_archive.close()
        atomic_json(args.result, result)
        print(json.dumps(result, indent=2), flush=True)
    print("M144_M120_LAYER0_BOUNDARY_MEASURED" if result["status"] == "MEASURED" else "M144_M120_LAYER0_BOUNDARY_FAIL")
    return 0 if result["status"] == "MEASURED" else 1


if __name__ == "__main__":
    raise SystemExit(main())
