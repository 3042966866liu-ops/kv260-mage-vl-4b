#!/usr/bin/env python3
"""Project sequence-batched Prefill traffic and HLS cycles from the model index."""

from __future__ import annotations

import argparse
import json
import math
from pathlib import Path


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--index", type=Path, required=True)
    parser.add_argument("--tokens", type=int, default=35)
    parser.add_argument("--max-tokens", type=int, default=64)
    parser.add_argument("--token-lanes", type=int, default=16)
    parser.add_argument("--max-blocks", type=int, default=560)
    parser.add_argument("--clock-mhz", type=float, default=166.666667)
    parser.add_argument("--dataflow", action="store_true")
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()

    if not 1 <= args.tokens <= args.max_tokens:
        raise ValueError("tokens must fit in one sequence tile")
    index = json.loads(args.index.read_text())
    active_batches = math.ceil(args.tokens / args.token_lanes)
    total_batches = args.max_tokens // args.token_lanes
    # HLS report: each active batch is 92 cycles, a skipped batch is 2 cycles,
    # plus two cycles of function control. Weight loading is 21 cycles and the
    # block-loop wrapper contributes four cycles.
    if args.dataflow:
        # Packed 16-FIFO DATAFLOW report: 10 cycles with no active batch and
        # +52 cycles per active batch, reaching 218 cycles for all four.
        compute_cycles_per_block = 10 + 52 * active_batches
    else:
        compute_cycles_per_block = 2 + 92 * active_batches + 2 * (
            total_batches - active_batches
        )
    block_cycles = 21 + compute_cycles_per_block + 4
    # Packed activation loader report is 257..641 cycles for 0..64 valid tokens.
    activation_load_cycles = 257 + 6 * args.tokens

    weight_bytes = 0
    activation_bytes = 0
    output_bytes = 0
    macro_cycles = 0
    activation_cycles = 0
    clear_write_cycles = 0
    calls = 0
    group_blocks = 0
    for linear in index["linears"]:
        groups = int(linear["input_groups"])
        blocks = int(linear["output_blocks"])
        chunks = math.ceil(blocks / args.max_blocks)
        calls += chunks
        weight_bytes += int(linear["bytes"])
        activation_bytes += groups * chunks * args.tokens * 80
        output_bytes += args.tokens * blocks * 32
        group_blocks += groups * blocks
        macro_cycles += groups * blocks * block_cycles
        activation_cycles += groups * chunks * activation_load_cycles
        clear_write_cycles += 5 * args.tokens * blocks

    total_cycles = macro_cycles + activation_cycles + clear_write_cycles
    result = {
        "format": "tellme-prefill-roofline-v1",
        "tokens": args.tokens,
        "max_tokens": args.max_tokens,
        "token_lanes": args.token_lanes,
        "max_output_blocks": args.max_blocks,
        "clock_mhz": args.clock_mhz,
        "linear_count": len(index["linears"]),
        "kernel_calls": calls,
        "group_blocks": group_blocks,
        "active_token_batches": active_batches,
        "dataflow": args.dataflow,
        "compute_cycles_per_block": compute_cycles_per_block,
        "block_cycles": block_cycles,
        "activation_load_cycles": activation_load_cycles,
        "traffic_bytes": {
            "weights": weight_bytes,
            "activations": activation_bytes,
            "outputs": output_bytes,
            "total": weight_bytes + activation_bytes + output_bytes,
        },
        "cycles": {
            "group_block": macro_cycles,
            "activation_load": activation_cycles,
            "clear_and_output": clear_write_cycles,
            "total": total_cycles,
        },
        "projected_hls_seconds": total_cycles / (args.clock_mhz * 1.0e6),
    }
    encoded = json.dumps(result, indent=2, sort_keys=True) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(encoded)
    print(encoded, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
