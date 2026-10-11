"""Read-only historical/profile and HLS-source audit. Never accesses hardware."""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
from pathlib import Path
import sys

sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parents[1]


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def audit(root: Path = ROOT) -> dict:
    profile_path = root / "deployment/mage_vl4b/M239_FULL849_PROFILE_BOARD_RESULT_02.json"
    kernel_path = root / "hls/mage_prefill_m89x_runtime/mage_prefill_m89x_runtime.cpp"
    p = json.loads(profile_path.read_text(encoding="utf-8"))["profile"]
    if p["build_id"].lower() != "0x4d395832" or p["tokens"] != 849 or p["layers_completed"] != 36:
        raise ValueError("unexpected historical profile identity")
    if p["logical_calls"] != 154 * math.ceil(p["tokens"] / 32) + 8:
        raise ValueError("historical logical-call identity mismatch")
    if p["physical_calls"] != p["logical_calls"] + p["scale_retry_count"]:
        raise ValueError("physical-call retry identity mismatch")
    families: dict[str, float] = {}
    for key, value in p["family_wall_ms"].items():
        if not math.isfinite(value) or value < 0:
            raise ValueError("invalid family timing")
        family = key.split(":", 1)[1]
        families[family] = families.get(family, 0) + value
    if not math.isclose(sum(families.values()), p["family_wall_total_ms"], abs_tol=0.001):
        raise ValueError("family timing conservation failure")
    source = kernel_path.read_text(encoding="utf-8")
    markers = ["ap_int<24> dot00", "m89o_dot(weight0", "float acc0[32][4]",
               "(float)dot00 * activation0 * scale0", "for (unsigned token_pair = 0; token_pair < 16"]
    if not all(m in source for m in markers):
        raise ValueError("arithmetic source structure changed; manual review required")
    return {
        "gate": "M316-offline-historical-profile-and-source-audit",
        "status": "PASS_OFFLINE_AUDIT_NOT_NEW_PERFORMANCE",
        "sources": {str(path.relative_to(root)): sha(path) for path in (profile_path, kernel_path)},
        "historical_build_id": p["build_id"],
        "current_source_matches_bitstream_proved": False,
        "historical_prefill_ms": p["prefill_wall_ms"],
        "historical_family_ms": families,
        "historical_mlp_share": (families["gate_up"] + families["mlp_down"]) / p["prefill_wall_ms"],
        "phase_sum_ms_not_additive": sum(p["runtime_phase_ms"].values()),
        "phase_accounting_warning": "Nested/overlapping phase totals are not a disjoint wall-time partition; do not sum them to attribute bottlenecks.",
        "integer_dot_then_fp32_scale_already_in_source": True,
        "rejected_duplicate_optimization": "Introducing grouped integer dots as if absent; source already does it.",
        "retained_numerical_constraints": ["FP16 subnormal scale expansion", "FP32 cross-group accumulation", "final FP16 output rounding"],
        "not_measured_offline": ["AXI effective bandwidth", "FPGA compute vs memory stalls", "new kernel latency", "power", "semantic quality"],
        "next_small_measurement": "One real Gate/Up or Down transaction; distinguish bytes, cycles, stalls, scale and control. No full E2E exploration.",
        "board_execution_run": False,
        "new_speedup_claim_allowed": False,
    }


def write_result(path: Path, result: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    data = (json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True, allow_nan=False) + "\n").encode("utf-8")
    partial = path.with_suffix(path.suffix + ".partial")
    partial.write_bytes(data)
    os.replace(partial, path)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--result", type=Path, required=True)
    args = parser.parse_args()
    try:
        result = audit()
    except Exception as error:
        write_result(args.result, {"status": "FAIL_OFFLINE", "error": f"{type(error).__name__}: {error}", "board_execution_run": False})
        raise
    write_result(args.result, result)
    print("M316_OFFLINE_AUDIT_PASS", "mlp_share=", result["historical_mlp_share"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
