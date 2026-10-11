#!/usr/bin/env python3
"""Local regression: UART-safe QKV helper must equal the saved independent reference."""

from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

import numpy as np


def main() -> int:
    workspace = Path(__file__).resolve().parents[1]
    sys.path.insert(0, str(workspace / "scripts"))
    sys.path.insert(0, str(workspace / "deployment/mage_vl4b/m89x_t32_runtime"))
    from contract_runtime import RuntimeContract, quantize_t32
    from m89x1_qkv_reference_helper import deterministic_input, reference_descriptor

    root = workspace / "deployment/mage_vl4b"
    contract = RuntimeContract.load(root / "M89X_MERGED_RUNTIME_CONTRACT_RESULT.json", "PASS_MERGED_648_TILE_RUNTIME_CONTRACT")
    chain = next(item for item in contract.chains if int(item["layer"]) == 0 and item["family"] == "qkv")
    _, codes, scales = quantize_t32(deterministic_input(), int(chain["groups"]))
    shards = [root / "artifacts/m89y_language_fourport" / f"weights{i}.bin" for i in range(4)]
    actual: dict[str, np.ndarray] = {}
    for descriptor in chain["descriptors"]:
        value = reference_descriptor(shards, descriptor, chain, codes, scales)
        name, start = descriptor["module"], int(descriptor["row_start"])
        stop = start + int(descriptor["valid_rows"])
        prior = actual.get(name, np.zeros((32, stop), dtype="<f2"))
        if prior.shape[1] < stop:
            grown = np.zeros((32, stop), dtype="<f2")
            grown[:, :prior.shape[1]] = prior
            prior = grown
        prior[:, start:stop] = value[:, :int(descriptor["valid_rows"])]
        actual[name] = prior
    with np.load(root / "m89x_t32_runtime/layer0_qkv_reference.npz") as expected:
        hashes = {name: hashlib.sha256(actual[name].tobytes()).hexdigest() for name in expected.files}
        passed = all(np.array_equal(actual[name], expected[name]) for name in expected.files)
    print("M89X1_QKV_REFERENCE_HELPER_REGRESSION_PASS" if passed else "M89X1_QKV_REFERENCE_HELPER_REGRESSION_FAIL")
    print(json.dumps(hashes, sort_keys=True))
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
