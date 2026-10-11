#!/usr/bin/env python3
"""Measure FP32 accumulation against the retained FP16 QKV reference."""

from __future__ import annotations

import hashlib
import json
import struct
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


def deterministic_input() -> np.ndarray:
    index = np.arange(32 * 2560, dtype=np.float32).reshape(32, 2560)
    return (np.sin(index * np.float32(0.001)) * np.float32(0.25)).astype(np.float32)


def axis64_bytes(values: np.ndarray) -> bytes:
    array = np.asarray(values, dtype="<f2")
    blocks = array.shape[1] // 32
    words = array.reshape(32, 4, blocks, 4, 2).transpose(2, 0, 1, 3, 4).reshape(-1, 2).view("<u2")
    payload = bytearray()
    for low, high in words:
        payload.extend(struct.pack("<H2xH2x", int(low), int(high)))
    return bytes(payload)


def metrics(expected: np.ndarray, actual: np.ndarray) -> dict:
    e, a = expected.astype(np.float32), actual.astype(np.float32)
    delta = a - e
    return {
        "elements": int(e.size),
        "fp16_exact_count": int(np.count_nonzero(a == e)),
        "max_abs": float(np.max(np.abs(delta))),
        "mean_abs": float(np.mean(np.abs(delta))),
        "rmse": float(np.sqrt(np.mean(np.square(delta)))),
        "relative_l2": float(np.linalg.norm(delta) / np.linalg.norm(e)),
        "cosine": float(np.dot(a.ravel(), e.ravel()) / (np.linalg.norm(a) * np.linalg.norm(e))),
    }


def main() -> int:
    candidate = ROOT / "deployment" / "mage_vl4b" / "m89x_board_candidate"
    contract = json.loads((candidate / "contracts" / "M89X_MERGED_RUNTIME_CONTRACT_RESULT.json").read_text())
    chain = next(item for item in contract["chains"] if int(item["layer"]) == 0 and item["family"] == "qkv")
    auxiliary = np.load(candidate / "auxiliary" / "m77_text_aux_fp16.npz", allow_pickle=False)
    try:
        norm_weight = np.asarray(auxiliary["model.language_model.layers.0.input_layernorm.weight"], dtype=np.float32)
    finally:
        auxiliary.close()
    values = rms_norm(deterministic_input(), norm_weight)
    _, codes, activation_scales = quantize_t32(values, int(chain["groups"]))
    shards = [ROOT / "deployment" / "mage_vl4b" / "artifacts" / "m89y_language_fourport" / f"weights{i}.bin" for i in range(4)]

    payload = bytearray()
    matrices = []
    for descriptor in chain["descriptors"]:
        rows = int(descriptor["rows_per_shard"])
        blocks = rows // 8
        offset_words = int(descriptor["offset_words"])
        per_shard = []
        for shard in shards:
            accumulated = np.zeros((32, 8), dtype=np.float32)
            with shard.open("rb", buffering=0) as source:
                for group in range(int(chain["groups"])):
                    source.seek((offset_words + group * blocks * 9) * 16)
                    record = np.frombuffer(source.read(9 * 16), dtype=np.uint8).reshape(9, 16)
                    decoded, weight_scales = _decode_w2(record)
                    dots = codes[:, group].astype(np.int32) @ decoded.astype(np.int32).T
                    accumulated += dots.astype(np.float32) * np.float32(activation_scales[:, group, None]) * np.float32(weight_scales[None, :])
            per_shard.append(accumulated.astype("<f2"))
        matrix = np.concatenate(per_shard, axis=1)
        matrices.append(matrix)
        payload.extend(axis64_bytes(matrix))

    output_path = ROOT / "deployment" / "mage_vl4b" / "artifacts" / "m89x1_layer0_norm_qkv_fp32_accum_candidate.bin"
    output_path.write_bytes(payload)
    expected_path = ROOT / "deployment" / "mage_vl4b" / "artifacts" / "m89x1_layer0_norm_qkv_python_expected.bin"
    expected_raw = expected_path.read_bytes()
    expected_values = np.frombuffer(expected_raw, dtype=np.uint8).reshape(-1, 8)[:, [0, 1, 4, 5]].reshape(-1).view("<f2")
    actual_values = np.concatenate([matrix.reshape(-1) for matrix in matrices])
    result = {
        "gate": "M89-X1-rmsnorm-qkv-accumulation-variant-study",
        "status": "MEASURED",
        "variant": "float32 scale multiply and accumulation; fp16 final output",
        "output_sha256": hashlib.sha256(payload).hexdigest(),
        "comparison_to_retained_fp16_reference": metrics(expected_values, actual_values),
    }
    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
