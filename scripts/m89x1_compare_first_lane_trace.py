#!/usr/bin/env python3
"""Compare one RMSNorm-QKV lane at every FP16 operation boundary."""

from __future__ import annotations

import csv
import json
import sys
from pathlib import Path

import numpy as np


ROOT = Path(__file__).resolve().parents[1]
RUNTIME = ROOT / "deployment" / "mage_vl4b" / "m89x_board_candidate" / "runtime"
sys.path.insert(0, str(RUNTIME))
from contract_runtime import quantize_t32  # noqa: E402
from text_e2e_gate import rms_norm  # noqa: E402
sys.path.insert(0, str(ROOT / "scripts"))
from m89x1_qkv_reference_helper import _decode_w2  # noqa: E402


def bits(value: np.float16) -> int:
    return int(np.asarray(value, dtype="<f2").view("<u2"))


def float_bits(value: np.float32) -> int:
    return int(np.asarray(value, dtype="<f4").view("<u4"))


def deterministic_input() -> np.ndarray:
    index = np.arange(32 * 2560, dtype=np.float32).reshape(32, 2560)
    return (np.sin(index * np.float32(0.001)) * np.float32(0.25)).astype(np.float32)


def main() -> int:
    candidate = ROOT / "deployment" / "mage_vl4b" / "m89x_board_candidate"
    contract = json.loads((candidate / "contracts" / "M89X_MERGED_RUNTIME_CONTRACT_RESULT.json").read_text())
    chain = next(item for item in contract["chains"] if int(item["layer"]) == 0 and item["family"] == "qkv")
    descriptor = chain["descriptors"][0]
    auxiliary = np.load(candidate / "auxiliary" / "m77_text_aux_fp16.npz", allow_pickle=False)
    try:
        weight = np.asarray(auxiliary["model.language_model.layers.0.input_layernorm.weight"], dtype=np.float32)
    finally:
        auxiliary.close()
    values = rms_norm(deterministic_input(), weight)
    _, codes, activation_scales = quantize_t32(values, int(chain["groups"]))

    rows = int(descriptor["rows_per_shard"])
    blocks = rows // 8
    offset_words = int(descriptor["offset_words"])
    shard = ROOT / "deployment" / "mage_vl4b" / "artifacts" / "m89y_language_fourport" / "weights0.bin"
    python_rows = []
    with shard.open("rb", buffering=0) as source:
        records = []
        for group in range(40):
            source.seek((offset_words + group * blocks * 9) * 16)
            records.append(np.frombuffer(source.read(9 * 16), dtype=np.uint8).reshape(9, 16))
    for token in range(2):
        acc = np.float32(0)
        for group, record in enumerate(records):
            decoded, weight_scales = _decode_w2(record)
            dot = int(codes[token, group].astype(np.int32) @ decoded[0].astype(np.int32))
            activation_scale = np.float32(np.float16(activation_scales[token, group]))
            weight_scale = np.float32(np.float16(weight_scales[0]))
            mul1 = np.float32(np.float32(dot) * activation_scale)
            term = np.float32(mul1 * weight_scale)
            acc = np.float32(acc + term)
            python_rows.append({
                "token": token,
                "group": group,
                "dot": dot,
                "activation_bits": bits(np.float16(activation_scale)),
                "weight_bits": bits(np.float16(weight_scale)),
                "mul1_float_bits": float_bits(mul1),
                "term_float_bits": float_bits(term),
                "acc_float_bits": float_bits(acc),
                "acc_half_bits": bits(np.float16(acc)),
            })

    trace_path = ROOT / "deployment" / "mage_vl4b" / "artifacts" / "m89x2_layer0_norm_qkv_hls_token01_trace.csv"
    with trace_path.open(newline="") as handle:
        hls_rows = [{key: int(value) for key, value in row.items()} for row in csv.DictReader(handle)]
    fields = ["dot", "activation_bits", "weight_bits", "mul1_float_bits",
              "term_float_bits", "acc_float_bits", "acc_half_bits"]
    mismatches = []
    for expected, observed in zip(python_rows, hls_rows):
        differing = [field for field in fields if expected[field] != observed[field]]
        if differing:
            mismatches.append({
                "token": expected["token"],
                "group": expected["group"],
                "fields": differing,
                "python": expected,
                "hls": observed,
            })
    result = {
        "gate": "M89-X1-rmsnorm-qkv-first-lane-operation-trace",
        "status": "MATCH" if not mismatches else "MISMATCH",
        "groups": len(python_rows),
        "mismatch_groups": len(mismatches),
        "first_mismatch": mismatches[0] if mismatches else None,
    }
    print(json.dumps(result, indent=2))
    return 0 if not mismatches else 1


if __name__ == "__main__":
    raise SystemExit(main())
