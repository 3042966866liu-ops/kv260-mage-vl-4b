#!/usr/bin/env python3
"""Fail-closed collector for M329 CPU-reference and stable-PL UART evidence."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import statistics
from pathlib import Path


BUILD_ID_DECIMAL = 0x4D395832
FIXTURE_SHA256 = "f384f45eea4bc14110a7add49dd0944f0a025403aecc3360369ec999e28257d9"
EXPECTED = {
    0: ("c03f51cc7cd6d157e04bd0da674ee59652168b58473d6d3b2070f58fe30ec3a0",
        "7167dff9da96757a768b44254403d1a439615fffbca3139ee5bfd261fa3c7a2d"),
    1: ("9dfa69036b7974a37ede922ddf46f4d9e9995f6f682e03e72b27e8867d879bb8",
        "fa47a9b8a152fe9c23a2b75d0d240efa2c9424f3e0f7f6a4ca793bd4847272ad"),
}


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def json_objects(raw: str) -> list[dict]:
    decoder = json.JSONDecoder()
    objects = []
    cursor = 0
    while (cursor := raw.find("{", cursor)) >= 0:
        try:
            value, length = decoder.raw_decode(raw[cursor:])
        except json.JSONDecodeError:
            cursor += 1
            continue
        if isinstance(value, dict) and "gate" in value:
            objects.append(value)
        cursor += length
    return objects


def require(condition: bool, message: str) -> None:
    if not condition:
        raise RuntimeError(message)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cpu-log", type=Path, required=True)
    parser.add_argument("--pl-log", type=Path, required=True)
    parser.add_argument("--hash-log", type=Path, required=True)
    parser.add_argument("--result", type=Path, required=True)
    args = parser.parse_args()
    if args.result.exists():
        parser.error("refusing to overwrite existing result")

    cpu_text = args.cpu_log.read_text(encoding="utf-8", errors="replace")
    pl_text = args.pl_log.read_text(encoding="utf-8", errors="replace")
    hash_text = args.hash_log.read_text(encoding="utf-8", errors="replace")
    cpu = [item for item in json_objects(cpu_text) if item.get("gate") == "M329-M120-same-fixture-CPU-arithmetic"]
    pl_matches = [item for item in json_objects(pl_text) if item.get("gate") == "M329-M120-stable-PL-same-fixture-timing"]
    env_matches = [item for item in json_objects(pl_text) if item.get("gate") == "M136-M120-board-environment"]
    require("__M329_CPU_RC_0__" in cpu_text and "M329_CPU_BOARD_NUMERICAL_PASS" in cpu_text,
            "CPU command did not finish cleanly")
    require("__M329_PL_RC_0__" in pl_text and "M329_PL_FIXTURE_GATE_PASS" in pl_text,
            "PL command did not finish cleanly")
    require("__M329_RESULTS_RC_0__" in hash_text, "result hash collection did not finish cleanly")
    require(len(cpu) == 7 and len(pl_matches) == 1 and len(env_matches) == 1,
            "missing or extra gate JSON objects")
    cpu.sort(key=lambda item: item["case_ordinal"])
    pl = pl_matches[0]
    env = env_matches[0]
    require([item["case_ordinal"] for item in cpu] == list(range(7)), "CPU case closure mismatch")
    require(env["status"] == "PASS" and env["euid"] == 0 and env["xcl_probe_count"] == 1
            and env["pynq_device_count"] == 1 and env["xilinx_xrt"] == "/usr"
            and env["tmpdir"] == "/dev/shm"
            and env["xclbinutil"] == "/usr/local/share/pynq-venv/bin/xclbinutil"
            and env["package_manifest_sha256"] == "7600ba1af87680fe1294ae6dc88f8e0968f23b2e38ca48dbfd316e351ea76e3e",
            "same-terminal environment preflight mismatch")
    require(pl["status"] == "PASS_STABLE_PL_FIXTURE_TIMING"
            and pl["build_id_expected"].lower() == f"0x{BUILD_ID_DECIMAL:08x}"
            and pl["fixture_sha256"] == FIXTURE_SHA256
            and pl["host_machine"] == "aarch64" and pl["dma_safe_to_release"] is True
            and pl["repeat"] == 3 and len(pl["cases"]) == 2,
            "PL result identity or closure mismatch")

    for item in cpu:
        require(item["status"] == "PASS_CPU_NUMERICAL_ONLY"
                and item["host_machine"] == "aarch64"
                and item["fixture_sha256"] == FIXTURE_SHA256
                and item["repeat"] == 3 and len(item["runs"]) == 3
                and all(run["full_output_exact"] and run["output_sha256"] == item["expected_output_sha256"]
                        for run in item["runs"]),
                f"CPU case {item['case_ordinal']} failed full-output validation")
    summaries = []
    for pl_case in pl["cases"]:
        ordinal = pl_case["ordinal"]
        require(ordinal in EXPECTED and len(pl_case["runs"]) == 3, "PL case closure mismatch")
        cpu_case = cpu[ordinal]
        original_sha, ftz_sha = EXPECTED[ordinal]
        require(cpu_case["expected_output_sha256"] == original_sha
                and pl_case["expected_output_sha256_ftz"] == ftz_sha,
                "predeclared full-output identity mismatch")
        require(cpu_case["input_packet_sha256"] == pl_case["input_packet_sha256"]
                and cpu_case["weight_shard_sha256"] == pl_case["weight_shard_sha256"],
                "CPU/PL input or weight identity mismatch")
        for run in pl_case["runs"]:
            snap = run["snapshot"]
            require(run["full_output_ftz_exact"] and run["observed_output_sha256"] == ftz_sha
                    and snap["ap_return"] == BUILD_ID_DECIMAL
                    and snap["mm2s_idle"] and snap["s2mm_idle"]
                    and not snap["mm2s_error"] and not snap["s2mm_error"],
                    f"PL case {ordinal} numerical/DMA status mismatch")
        med = lambda records, key: statistics.median(float(run[key]) for run in records)
        summaries.append({
            "ordinal": ordinal, "bits": pl_case["bits"], "descriptor_count": 2,
            "identity": pl_case["identity"], "cpu_output_sha256": original_sha,
            "pl_output_sha256_ftz": ftz_sha,
            "cpu_reference_total_median_ms": med(cpu_case["runs"], "total_ms"),
            "cpu_reference_decode_median_ms": med(cpu_case["runs"], "decode_ms"),
            "cpu_reference_integer_dot_median_ms": med(cpu_case["runs"], "integer_dot_and_accumulate_ms"),
            "pl_transaction_total_median_ms": med(pl_case["runs"], "total_ms"),
            "pl_dma_launch_wait_median_ms": med(pl_case["runs"], "dma_launch_and_completion_wait_ms"),
            "pl_weight_stage_sync_median_ms": med(pl_case["runs"], "weight_stage_and_sync_ms"),
        })

    hash_pairs = re.findall(r"(?m)^([0-9a-f]{64})\s+(/home/ubuntu/tellme_m329_cpu_reference_20260926/results/[^\s]+\.json)$", hash_text)
    remote_hashes = {path: digest for digest, path in hash_pairs}
    require(len(hash_pairs) == len(remote_hashes), "duplicate remote result paths")
    expected_paths = [f"/home/ubuntu/tellme_m329_cpu_reference_20260926/results/case_{i}.json"
                      for i in range(7)]
    expected_paths += ["/home/ubuntu/tellme_m329_cpu_reference_20260926/results/pl_environment.json",
                       "/home/ubuntu/tellme_m329_cpu_reference_20260926/results/pl_fixture.json"]
    require(set(remote_hashes) == set(expected_paths), "remote result file list mismatch")

    result = {
        "gate": "M329-KV260-same-fixture-CPU-PL-comparison",
        "status": "PASS_SAME_INPUT_IMPLEMENTATION_AB",
        "scope": "One frozen real-record fixture, not whole-model or video acceleration",
        "build_id": f"0x{BUILD_ID_DECIMAL:08x}",
        "fixture_sha256": FIXTURE_SHA256,
        "cpu_case_count": 7,
        "cpu_repeats_per_case": 3,
        "pl_case_count": 2,
        "pl_repeats_per_case": 3,
        "same_input_and_weight_identity": True,
        "numerical_contract": "CPU full output exact original FP16; PL full output exact after frozen FP16 subnormal-to-signed-zero canonicalization",
        "summaries": summaries,
        "pl_overlay_load_ms_excluded": pl["overlay_load_ms"],
        "measurement_limitation": "CPU reference is Python/NumPy, not optimized A53 NEON; CPU and PL were measured sequentially, not counterbalanced. No model-wide speedup or end-to-end video gain is inferred.",
        "remote_result_sha256": remote_hashes,
        "uart_log_sha256": {
            "cpu": sha256_file(args.cpu_log), "pl": sha256_file(args.pl_log),
            "result_hashes": sha256_file(args.hash_log),
        },
        "stable_rollback_preserved": True,
        "next_step": "Repeat with optimized A53 CPU kernel and counterbalanced order; then profile full video path before claiming model-level PL benefit.",
    }
    args.result.parent.mkdir(parents=True, exist_ok=True)
    temporary = args.result.with_name(args.result.name + f".partial-{os.getpid()}")
    temporary.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    os.replace(temporary, args.result)
    print(json.dumps({"status": result["status"], "summaries": summaries}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
