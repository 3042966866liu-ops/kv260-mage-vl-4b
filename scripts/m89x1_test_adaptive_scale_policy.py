#!/usr/bin/env python3
"""Pure-host regression for the adaptive HS64 overflow guard."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--result", type=Path)
    args = parser.parse_args()
    workspace = Path(__file__).resolve().parents[1]
    runtime_root = workspace / "deployment/mage_vl4b/m89x_t32_runtime"
    sys.path.insert(0, str(runtime_root))
    from board_runtime import M89XBoardRuntime, MAX_TRANSMITTED_ACTIVE_SCALE
    from contract_runtime import quantize_t32

    small = np.full((30, 2560), np.float32(1.0))
    overflow_case = np.zeros((30, 9728), dtype=np.float32)
    overflow_case[0, 0] = np.float32(-2512.48046875)
    zero = np.zeros((30, 2560), dtype=np.float32)
    selected = {
        "zero": M89XBoardRuntime._initial_scale_shift(zero),
        "small": M89XBoardRuntime._initial_scale_shift(small),
        "layer6_mlp_down": M89XBoardRuntime._initial_scale_shift(overflow_case),
    }
    _, _, transmitted = quantize_t32(
        overflow_case, 152, activation_scale_shift=selected["layer6_mlp_down"])
    active_max = float(np.max(transmitted[:overflow_case.shape[0]]))
    checks = {
        "zero_retains_shift6": selected["zero"] == 6,
        "small_retains_shift6": selected["small"] == 6,
        "layer6_case_reduces_shift": selected["layer6_mlp_down"] == 4,
        "active_scale_headroom": active_max <= MAX_TRANSMITTED_ACTIVE_SCALE,
        "finite_helper_accepts": M89XBoardRuntime._all_outputs_finite(
            {"x": np.zeros((2, 2), np.float32)}),
        "finite_helper_rejects_inf": not M89XBoardRuntime._all_outputs_finite(
            {"x": np.array([[np.inf]], np.float32)}),
        "finite_helper_rejects_nan": not M89XBoardRuntime._all_outputs_finite(
            {"x": np.array([[np.nan]], np.float32)}),
    }
    sparse_chain = {
        "descriptors": [{
            "module": "lm_head", "row_start": 8, "valid_rows": 4,
        }]
    }
    sparse = np.full((32, 12), np.nan, dtype=np.float32)
    sparse[:, 8:12] = np.float32(1.0)
    checks["sparse_unwritten_sentinels_allowed"] = M89XBoardRuntime._written_outputs_finite(
        sparse_chain, {"lm_head": sparse})
    sparse_bad = sparse.copy()
    sparse_bad[0, 9] = np.inf
    checks["sparse_written_inf_rejected"] = not M89XBoardRuntime._written_outputs_finite(
        sparse_chain, {"lm_head": sparse_bad})
    checks["sparse_missing_module_rejected"] = not M89XBoardRuntime._written_outputs_finite(
        sparse_chain, {})
    try:
        M89XBoardRuntime._initial_scale_shift(np.array([[np.inf]], np.float32))
        checks["nonfinite_input_rejected"] = False
    except FloatingPointError:
        checks["nonfinite_input_rejected"] = True
    passed = all(checks.values())
    result = {
        "gate": "M89-X1-adaptive-power-of-two-scale-policy",
        "status": "PASS" if passed else "FAIL",
        "selected_shifts": selected,
        "layer6_active_transmitted_scale_max": active_max,
        "maximum_transmitted_active_scale": MAX_TRANSMITTED_ACTIVE_SCALE,
        "checks": checks,
        "guarantee": (
            "Every family rejects a non-finite input, checks every descriptor-written FPGA element, "
            "and retries the same family at successively lower shifts through zero before allowing "
            "propagation. Structural sparse-chain sentinels are checked only after full assembly."
        ),
    }
    if args.result is not None:
        args.result.parent.mkdir(parents=True, exist_ok=True)
        temporary = args.result.with_suffix(args.result.suffix + ".tmp")
        temporary.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
        temporary.replace(args.result)
    print(json.dumps(result, indent=2))
    print("M89X1_ADAPTIVE_SCALE_POLICY_PASS" if passed else "M89X1_ADAPTIVE_SCALE_POLICY_FAIL")
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
