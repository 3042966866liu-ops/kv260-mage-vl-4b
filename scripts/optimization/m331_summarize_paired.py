#!/usr/bin/env python3
"""Fail-closed summary of M331's ten per-shape counterbalanced pairs."""
import argparse
import json
import os
import statistics
from pathlib import Path


def median(values):
    return statistics.median(values)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--board-result", type=Path, required=True)
    parser.add_argument("--summary", type=Path, required=True)
    args = parser.parse_args()
    if args.summary.exists():
        raise RuntimeError("refusing to overwrite prior M331 summary")
    data = json.loads(args.board_result.read_text(encoding="utf-8"))
    if data.get("status") != "PASS_PAIRED_FIXTURE_AB" or data.get("build_id_expected") != "0x4d395832":
        raise RuntimeError("board gate or stable Build-ID failed")
    if data.get("dma_safe_to_release") is not True or len(data.get("cases", [])) != 2:
        raise RuntimeError("DMA release evidence or case count failed")
    summaries = []
    for ordinal, case in enumerate(data["cases"]):
        if case["ordinal"] != ordinal or case["bits"] != (2 if ordinal == 0 else 4):
            raise RuntimeError("shape identity mismatch")
        pairs = case["pairs"]
        if len(pairs) != 10:
            raise RuntimeError("insufficient valid pairs")
        cpu, pl, ratios = [], [], []
        order_medians = {}
        for index, pair in enumerate(pairs):
            expected_order = "CPU-PL" if index % 2 == 0 else "PL-CPU"
            if pair["index"] != index or pair["execution_order"] != expected_order:
                raise RuntimeError("counterbalanced order mismatch")
            a, b = pair["cpu"], pair["pl"]
            if not a["full_original_fp16_exact"] or not b["full_fp16_ftz_output_exact"]:
                raise RuntimeError("complete output mismatch")
            if a["output_sha256"] != case["expected_cpu_output_sha256"] or b["output_sha256_ftz"] != case["expected_pl_output_sha256_ftz"]:
                raise RuntimeError("output SHA mismatch")
            snap = b["snapshot"]
            if (snap.get("ap_return") != 0x4D395832 or snap.get("mm2s_idle") is not True
                    or snap.get("s2mm_idle") is not True or snap.get("mm2s_error") is not False
                    or snap.get("s2mm_error") is not False):
                raise RuntimeError("Build-ID/DMA status mismatch")
            x, y = a["packed_compute_ms"], b["transaction_total_ms"]
            if x <= 0 or y <= 0:
                raise RuntimeError("non-positive timing")
            cpu.append(x)
            pl.append(y)
            ratios.append(x / y)
        for expected_order in ("CPU-PL", "PL-CPU"):
            chosen = [p for p in pairs if p["execution_order"] == expected_order]
            order_medians[expected_order] = {
                "cpu_ms": median([p["cpu"]["packed_compute_ms"] for p in chosen]),
                "pl_ms": median([p["pl"]["transaction_total_ms"] for p in chosen]),
            }
        summaries.append({
            "ordinal": ordinal, "bits": case["bits"], "valid_pairs": len(pairs),
            "cpu_packed_compute_median_ms": median(cpu), "cpu_range_ms": [min(cpu), max(cpu)],
            "pl_transaction_median_ms": median(pl), "pl_range_ms": [min(pl), max(pl)],
            "paired_cpu_over_pl_median": median(ratios),
            "paired_ratio_range": [min(ratios), max(ratios)],
            "order_medians": order_medians,
        })
    output = {
        "gate": "M331-paired-native-A53-stable-PL-analysis",
        "status": "PASS",
        "build_id": "0x4D395832",
        "valid_pairs_total": 20,
        "interpretation": "same-fixture single-chain implementation-level paired speed; not whole-model/video speedup",
        "summaries": summaries,
    }
    args.summary.parent.mkdir(parents=True, exist_ok=True)
    temp = args.summary.with_name(args.summary.name + f".partial-{os.getpid()}")
    temp.write_text(json.dumps(output, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    os.replace(temp, args.summary)
    print(json.dumps(summaries, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
