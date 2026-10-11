#!/usr/bin/env python3
"""One-chain diagnostic for an M89-X1 QKV hash mismatch.

This runner deliberately performs the same bounded Layer-0 QKV transaction as
the acceptance gate.  Unlike that gate, it records all three output hashes and
small numerical summaries before returning failure, so the next change can be
limited to the first divergent chain rather than guessing at full-model E2E.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
import time
from pathlib import Path

import numpy as np


EXPECTED = {
    "model.language_model.layers.0.self_attn.q_proj": "c126c0aec84f437ebbce28372fe35aa63692bcda1d7dc5bb25dd780d459f5086",
    "model.language_model.layers.0.self_attn.k_proj": "0b6e089c071e7c082eb96f8bc8dafef53c88c3129f755119ae41c328d747cd12",
    "model.language_model.layers.0.self_attn.v_proj": "1d402f0405681a2420886c38ea4eda1ce4cafa12b0132097dd31bc79fea4eecd",
}
EXPECTED_INPUT = "04457eb7f805ddb89bff1543e307844e7c6ccaa8f3593bbd18dda68cd23fa22f"


def digest(value: np.ndarray, dtype: str) -> str:
    return hashlib.sha256(np.ascontiguousarray(value, dtype=dtype).tobytes()).hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--candidate", type=Path, required=True)
    parser.add_argument("--result", type=Path, required=True)
    args = parser.parse_args()
    root = args.candidate
    sys.path.insert(0, str(root / "runtime"))
    from board_runtime import BUILD_ID, M89XBoardRuntime
    from contract_runtime import pack_chain_input

    output: dict[str, object] = {
        "gate": "M89-X1-layer0-qkv-hash-mismatch-diagnostic",
        "status": "FAIL",
        "base_package_manifest_sha256": "c4645fdf2ff1b299d3a7fb302fed72a8d50a95b658ad76e464c67a72a1a6cf50",
    }
    runtime = None
    started = time.monotonic()
    try:
        indices = np.arange(32 * 2560, dtype=np.float32).reshape(32, 2560)
        values = (np.sin(indices * np.float32(0.001)) * np.float32(0.25)).astype(np.float32)
        runtime = M89XBoardRuntime(
            root / "overlay/m89x_t32.bit",
            Path("/home/ubuntu/tellme_m89x_upload/m89y_language_fourport"),
            Path("/home/ubuntu/tellme_m89x_upload/m89z2_lmhead_w4_fourport"),
            root / "contracts/M89X_MERGED_RUNTIME_CONTRACT_RESULT.json",
            root / "contracts/M89Z2_LMHEAD_RUNTIME_CONTRACT_RESULT.json",
            "staged-low-cma",
        )
        chain = next(item for item in runtime.language_contract.chains
                     if int(item["layer"]) == 0 and item["family"] == "qkv")
        input_hash = hashlib.sha256(pack_chain_input(chain, values)).hexdigest()
        if input_hash != EXPECTED_INPUT:
            raise RuntimeError("deterministic input hash mismatch")
        observed = runtime.language_family(0, "qkv", values)
        details: dict[str, object] = {}
        all_match = True
        for name, expected in EXPECTED.items():
            value = np.asarray(observed.get(name), dtype=np.float32)
            if value.shape[0] != 32 or not np.isfinite(value).all():
                raise RuntimeError(f"invalid output {name}: shape={value.shape}")
            fp16 = digest(value, "<f2")
            match = fp16 == expected
            all_match = all_match and match
            details[name] = {
                "shape": list(value.shape),
                "expected_sha256_fp16": expected,
                "observed_sha256_fp16": fp16,
                "observed_sha256_fp32": digest(value, "<f4"),
                "match": match,
                "minimum": float(value.min()),
                "maximum": float(value.max()),
                "first_8_fp16_bits": np.asarray(value.reshape(-1)[:8], dtype="<f2").view("<u2").astype(int).tolist(),
            }
        evidence = runtime.evidence()
        if evidence["build_id"] != f"0x{BUILD_ID:08x}" or evidence["host_calls"] != 1:
            raise RuntimeError(f"runtime evidence mismatch: {evidence}")
        output.update(status="PASS" if all_match else "MISMATCH", evidence=evidence, outputs=details)
    except Exception as exc:
        output["error"] = f"{type(exc).__name__}: {exc}"
    finally:
        if runtime is not None:
            runtime.close()
        output["total_ms"] = (time.monotonic() - started) * 1000.0
        args.result.parent.mkdir(parents=True, exist_ok=True)
        args.result.write_text(json.dumps(output, indent=2) + "\n", encoding="utf-8")
        print(json.dumps(output, indent=2), flush=True)
    print("M89X1_QKV_DIAGNOSTIC_PASS" if output["status"] == "PASS" else "M89X1_QKV_DIAGNOSTIC_MISMATCH")
    return 0 if output["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
