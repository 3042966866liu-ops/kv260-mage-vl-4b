#!/usr/bin/env python3
"""Build a minimal M89-X1 CSim fixture for Layer-0 RMSNorm QKV.

The fixture deliberately uses the exact activation quantizer and packed W2
records used by the board contract, but its expected output is produced by the
independent packed-weight reference helper.  It is an offline diagnostic only.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import struct
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "deployment" / "mage_vl4b" / "m89x_board_candidate" / "runtime"))
from contract_runtime import quantize_t32  # noqa: E402
from text_e2e_gate import rms_norm  # noqa: E402
sys.path.insert(0, str(ROOT / "scripts"))
from m89x1_qkv_reference_helper import reference_descriptor  # noqa: E402

MAGIC = b"M89X1NQ"
TOKENS, MAX_CHAIN, MAX_WORDS = 32, 10, 17
LAYER = 0


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(8 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def deterministic_input() -> np.ndarray:
    index = np.arange(TOKENS * 2560, dtype=np.float32).reshape(TOKENS, 2560)
    return (np.sin(index * np.float32(0.001)) * np.float32(0.25)).astype(np.float32)


def hardware_order_bytes(values: np.ndarray) -> bytes:
    """Encode [token, 4*rows] FP16 output as the AXIS64 stream payload."""
    array = np.asarray(values, dtype="<f2")
    if array.shape[0] != TOKENS or array.shape[1] % (4 * 8):
        raise ValueError(f"invalid descriptor result shape {array.shape}")
    blocks = array.shape[1] // (4 * 8)
    ordered = array.reshape(TOKENS, 4, blocks, 4, 2).transpose(2, 0, 1, 3, 4)
    words = ordered.reshape(-1, 2).view("<u2")
    payload = bytearray()
    for low, high in words:
        payload.extend(struct.pack("<H", int(low)))
        payload.extend(b"\0\0")
        payload.extend(struct.pack("<H", int(high)))
        payload.extend(b"\0\0")
    return bytes(payload)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--candidate", type=Path, required=True)
    parser.add_argument("--fixture", type=Path, required=True)
    parser.add_argument("--expected", type=Path, required=True)
    parser.add_argument("--result", type=Path, required=True)
    args = parser.parse_args()

    candidate = args.candidate
    contract = json.loads((candidate / "contracts" / "M89X_MERGED_RUNTIME_CONTRACT_RESULT.json").read_text(encoding="utf-8"))
    chain = next(item for item in contract["chains"] if int(item["layer"]) == LAYER and item["family"] == "qkv")
    if int(chain["groups"]) != 40 or int(chain["bits"]) != 2 or len(chain["descriptors"]) != 4:
        raise RuntimeError("unexpected Layer-0 QKV geometry")
    aux = np.load(candidate / "auxiliary" / "m77_text_aux_fp16.npz", allow_pickle=False)
    try:
        prefix = "model.language_model.layers.0"
        values = rms_norm(deterministic_input(), np.asarray(aux[f"{prefix}.input_layernorm.weight"], dtype=np.float32))
    finally:
        aux.close()
    records, codes, scales = quantize_t32(values, int(chain["groups"]))
    language = ROOT / "deployment" / "mage_vl4b" / "artifacts" / "m89y_language_fourport"
    shards = [language / f"weights{index}.bin" for index in range(4)]
    if not all(item.is_file() for item in shards):
        raise RuntimeError("M89X1_NORM_QKV_LAYOUT_MISSING")

    # The diagnostic deliberately exercises one real eight-row block from every
    # Layer-0 QKV descriptor.  Keeping rows=8 means the CSim fixture tests the
    # exact scale/accumulation datapath without creating a fake compact layout
    # that would alter the kernel's group/block addressing rule.
    selected_block = 0
    expected = bytearray()
    expected_shapes: list[list[int]] = []
    for descriptor in chain["descriptors"]:
        reference = reference_descriptor(shards, descriptor, chain, codes, scales)
        rows = int(descriptor["rows_per_shard"])
        block_rows = np.concatenate([
            reference[:, shard * rows + selected_block * 8:shard * rows + (selected_block + 1) * 8]
            for shard in range(4)
        ], axis=1)
        expected.extend(hardware_order_bytes(block_rows))
        expected_shapes.append(list(block_rows.shape))

    args.fixture.parent.mkdir(parents=True, exist_ok=True)
    with args.fixture.open("wb") as output:
        output.write(MAGIC)
        output.write(struct.pack("<IIII", 1, MAX_CHAIN, TOKENS, TOKENS))
        output.write(struct.pack("<IIIIII", 0, LAYER, 0, len(chain["descriptors"]), int(chain["groups"]), int(chain["bits"])))
        handles = [path.open("rb") for path in shards]
        try:
            for descriptor in chain["descriptors"]:
                words = 9
                rows = int(descriptor["rows_per_shard"])
                blocks = rows // 8
                output.write(struct.pack("<BBBBI", 2, words, int(chain["groups"]), 0, selected_block))
                for handle in handles:
                    for group in range(int(chain["groups"])):
                        offset = (int(descriptor["offset_words"]) + (group * blocks + selected_block) * words) * 16
                        handle.seek(offset)
                        payload = handle.read(words * 16)
                        if len(payload) != words * 16:
                            raise RuntimeError("M89X1_NORM_QKV_SHORT_WEIGHT_READ")
                        output.write(payload)
                        output.write(bytes((MAX_WORDS - words) * 16))
        finally:
            for handle in handles:
                handle.close()
        output.write(records.tobytes())
    args.expected.write_bytes(bytes(expected))
    result = {
        "gate": "M89-X1-layer0-rmsnorm-qkv-csim-fixture",
        "status": "PASS_FIXTURE_BUILT",
        "classification": "offline diagnostic fixture; not a board or acceptance result",
        "fixture_sha256": sha256(args.fixture),
        "expected_sha256": sha256(args.expected),
        "fixture_bytes": args.fixture.stat().st_size,
        "expected_bytes": args.expected.stat().st_size,
        "activation_min": float(np.min(values)),
        "activation_max": float(np.max(values)),
        "non_unit_scale_count": int(np.count_nonzero(scales != np.float16(1))),
        "descriptor_output_shapes": expected_shapes,
    }
    args.result.parent.mkdir(parents=True, exist_ok=True)
    args.result.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result))
    print("M89X1_NORM_QKV_CSIM_FIXTURE_PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
