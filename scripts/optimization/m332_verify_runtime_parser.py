#!/usr/bin/env python3
"""Compare accepted and isolated M332 parser functions byte for byte.

No FPGA runtime is constructed and no package/fixture is modified.
"""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import sys
from pathlib import Path

sys.dont_write_bytecode = True

import numpy as np

from m332_parser_scale_bench import SHAPES, make_payload


ROOT = Path(__file__).resolve().parents[2]
STABLE = ROOT / "deployment/mage_vl4b/m242_m241_fixed_text_board_candidate"
BASE = ROOT / "deployment/mage_vl4b/m175_m120_fixed_text_candidate/runtime"
CANDIDATE = ROOT / "experiments/m332_parser_scale/board_package"
sys.path[:0] = [str(STABLE), str(BASE)]


def load(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load parser: {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module.M236PrefillRuntime._parse_into_and_check


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> int:
    argument_parser = argparse.ArgumentParser()
    argument_parser.add_argument("--output", type=Path)
    args = argument_parser.parse_args()
    reference = load(STABLE / "m236_prefill_runtime.py", "m332_stable_parser")
    candidate = load(CANDIDATE / "m236_prefill_runtime.py", "m332_candidate_parser")
    comparisons = []
    for ordinal, (name, width) in enumerate(SHAPES):
        payload = make_payload(width, 332 + ordinal)
        chain = {
            "output_bytes": len(payload),
            "descriptors": [{
                "output_bytes": len(payload),
                "rows_per_shard": width // 4,
                "valid_rows": width,
                "row_start": 0,
                "module": name,
            }],
        }
        for shift in range(7):
            for token_count in (1, 31, 32):
                baseline_target = {name: np.full((32, width), np.nan, dtype=np.float32)}
                candidate_target = {name: np.full((32, width), np.nan, dtype=np.float32)}
                baseline_finite = reference(
                    chain, payload, baseline_target, 0, token_count, shift
                )
                candidate_finite = candidate(
                    chain, payload, candidate_target, 0, token_count, shift
                )
                if baseline_finite is not True or candidate_finite is not True:
                    raise RuntimeError(f"unexpected finite flag: {name} shift={shift}")
                if baseline_target[name].tobytes() != candidate_target[name].tobytes():
                    raise RuntimeError(
                        f"full target bytes differ: {name} shift={shift} count={token_count}"
                    )
                comparisons.append([name, shift, token_count])
    result = {
        "gate": "M332-real-runtime-parser-offline-numerical",
        "status": "PASS_OFFLINE_NOT_BOARD",
        "comparison_count": len(comparisons),
        "stable_parser_sha256": sha256(STABLE / "m236_prefill_runtime.py"),
        "candidate_parser_sha256": sha256(CANDIDATE / "m236_prefill_runtime.py"),
        "compared_shapes": [list(pair) for pair in SHAPES],
        "scale_shifts": list(range(7)),
        "token_counts": [1, 31, 32],
        "complete_target_fp32_bits_exact": True,
        "not_proved": "A53 performance, video TTFT, DMA or FPGA correctness",
    }
    encoded = json.dumps(result, indent=2, sort_keys=True) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(encoded, encoding="utf-8")
    print(encoded, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
