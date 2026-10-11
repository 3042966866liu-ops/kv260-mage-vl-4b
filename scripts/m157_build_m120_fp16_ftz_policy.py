#!/usr/bin/env python3
"""Freeze the deterministic FP16 subnormal-to-signed-zero board contract."""

from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

import numpy as np


ROOT = Path(__file__).resolve().parents[1]
CANDIDATE = ROOT / "deployment/mage_vl4b/m120_text4b_board_candidate"
M156 = ROOT / "deployment/mage_vl4b/M156_M120_SINGLE_DESCRIPTOR_DIAGNOSTIC_RESULT_01.json"
OUTPUT = ROOT / "deployment/mage_vl4b/M157_M120_FP16_FTZ_POLICY_RESULT.json"


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def canonicalize(value: bytes) -> tuple[bytes, int]:
    words = np.frombuffer(value, dtype=np.uint8).copy().reshape(-1, 8)
    count = 0
    for start in (0, 4):
        bits = words[:, start:start + 2].copy().view("<u2").reshape(-1)
        subnormal = ((bits & np.uint16(0x7C00)) == 0) & ((bits & np.uint16(0x03FF)) != 0)
        count += int(np.count_nonzero(subnormal))
        bits[subnormal] &= np.uint16(0x8000)
        words[:, start:start + 2] = bits.view(np.uint8).reshape(-1, 2)
    return words.tobytes(), count


def main() -> int:
    sys.dont_write_bytecode = True
    runtime = CANDIDATE / "runtime"
    sys.path.insert(0, str(runtime))
    from m120_fixture import build_case, load_fixture

    fixture = CANDIDATE / "reference/m128_m120_real_record_csim_fixture.bin"
    case = load_fixture(fixture)[0]
    contracts = {}
    for level, descriptor_count in (("single-descriptor", 1), ("single-chain", 2)):
        built = build_case(case, descriptor_count)
        original = bytes(built["expected"])
        canonical, subnormal_count = canonicalize(original)
        contracts[level] = {
            "descriptor_count": descriptor_count,
            "identity": built["identity"],
            "input_bytes": len(built["packet"]),
            "output_bytes": len(canonical),
            "original_sha256": sha256_bytes(original),
            "canonical_sha256": sha256_bytes(canonical),
            "canonicalized_subnormal_count": subnormal_count,
        }
    diagnostic = json.loads(M156.read_text(encoding="utf-8"))
    measurement = diagnostic["measurement"]
    if measurement["status"] != "MEASURED":
        raise RuntimeError("M156 diagnostic is not MEASURED")
    if contracts["single-descriptor"]["canonical_sha256"] != measurement["observed_sha256"]:
        raise RuntimeError("FTZ canonical single-descriptor hash does not explain M156")
    first = measurement["first_differences"]
    if len(first) != 1 or int(first[0]["expected_fp16_bits"]) != 0x018F or int(first[0]["observed_fp16_bits"]) != 0:
        raise RuntimeError("M156 difference is not the expected isolated FP16 subnormal FTZ case")
    result = {
        "date": "2026-09-01",
        "gate": "M157-M120-FP16-FTZ-policy",
        "status": "PASS_POLICY_FROZEN_BEFORE_ACCEPTANCE_RERUN",
        "classification": "Offline deterministic output canonicalization policy; not a board acceptance or broader gate.",
        "candidate_build_id": "0x4D395832",
        "source_diagnostic": "deployment/mage_vl4b/M156_M120_SINGLE_DESCRIPTOR_DIAGNOSTIC_RESULT_01.json",
        "rule": {
            "name": "fp16-subnormal-to-signed-zero",
            "subnormal_test": "exponent==0 and mantissa!=0",
            "replacement": "preserve sign bit and clear exponent/mantissa",
            "normal_zero_infinity_nan_and_padding": "must remain bit exact",
            "tolerance_used": False,
        },
        "contracts": contracts,
        "acceptance_requirements": {
            "finite": True,
            "canonical_full_output_bit_exact": True,
            "padding_nonzero_count": 0,
            "build_id": "0x4D395832",
            "dma_idle_without_error": True,
        },
        "board_state_changed": False,
        "next_gate": "Rerun only the same single descriptor against the frozen canonical hash; single-chain remains locked.",
    }
    OUTPUT.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, indent=2))
    print("M157_M120_FP16_FTZ_POLICY_PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
