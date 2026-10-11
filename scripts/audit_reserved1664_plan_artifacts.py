#!/usr/bin/env python3
"""Recompute every file-backed SHA recorded by the M17 reserved1664 plan."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / "deployment/qwen25_3b_directddr_chain"
PLAN = BASE / "M17_RESERVED1664_PLAN.json"

PATHS = {
    "overlay_source_sha256": BASE / "user-override-reserved1664.overlay.dts",
    "dtb_sha256": BASE / "user-override-reserved1664.dtb",
    "boot_source_sha256": BASE / "boot_candidate_reserved1664.cmd",
    "boot_uimg_sha256": BASE / "boot_candidate_reserved1664.uimg",
    "driver_source_sha256": BASE / "reserved1664_mmap/tellme_reserved1664.c",
    "driver_ko_sha256": BASE / "reserved1664_mmap/tellme_reserved1664.ko",
    "runtime_reserved_pool_sha256": BASE / "runtime/reserved_ddr_pool.py",
    "runtime_mapping_smoke_sha256": BASE / "runtime/reserved_ddr_mapping_smoke.py",
    "runtime_resident_chain_sha256": BASE / "runtime/resident_chain_runtime.py",
    "runtime_full_e2e_sha256": BASE / "runtime/resident_full_e2e_gate.py",
    "runtime_chain_smoke_sha256": BASE / "runtime/chain_hardware_smoke.py",
    "runtime_memory_preflight_sha256": BASE / "runtime/resident_memory_preflight.py",
    "boot_preflight_sha256": BASE / "runtime/reserved1664_boot_preflight.py",
    "installer_sha256": BASE / "install_reserved1664_boot.sh",
    "rollback_sha256": BASE / "rollback_reserved1664_boot.sh",
    "full_gate_sha256": BASE / "run_reserved1664_full_gate.sh",
    "uart_runner_sha256": ROOT / "scripts/qwen3b_directddr_uart.ps1",
    "aggregator_unit_test_sha256": ROOT / "scripts/test_reserved1664_gate_aggregator.py",
    "matched_cpu_fpga_evidence_sha256": BASE / "M17_MATCHED_CPU_FPGA_EVIDENCE.json",
    "prompt_identity_probe_sha256": ROOT / "scripts/qwen3b_prompt_identity_probe.py",
    "board_model_identity_preflight_sha256": BASE / "runtime/board_model_identity_preflight.py",
    "board_model_identity_result_sha256": BASE / "RESERVED1664_BOARD_MODEL_IDENTITY_RESULT.json",
    "runtime_highddr_prefill_smoke_sha256": BASE / "runtime/highddr_prefill_smoke.py",
    "runtime_chain_common_sha256": BASE / "runtime/chain_common.py",
    "runtime_hostbo_pool_sha256": BASE / "runtime/hostbo_pool.py",
    "runtime_offline_ddr_pool_sha256": BASE / "runtime/offline_ddr_pool.py",
    "decode_highddr_bit_sha256": BASE / "overlay_highddr/qwen25_decode_directddr_chain_highddr.bit",
    "decode_highddr_hwh_sha256": BASE / "overlay_highddr/qwen25_decode_directddr_chain_highddr.hwh",
    "prefill_highddr_bit_sha256": BASE / "overlay_highddr_prefill/qwen25_shared_l40_highddr.bit",
    "prefill_highddr_hwh_sha256": BASE / "overlay_highddr_prefill/qwen25_shared_l40_highddr.hwh",
    "stable_runtime_sha256": ROOT / "deployment/qwen25_3b_no_final_forward/runtime/qwen_fpga_runtime.py",
    "stable_native_snapshot_sha256": BASE / "board_stable_prefill_native.cpython-310-aarch64-linux-gnu.so",
    "artifact_preflight_sha256": BASE / "runtime/reserved1664_artifact_preflight.py",
    "artifact_preflight_result_sha256": BASE / "RESERVED1664_ARTIFACT_PREFLIGHT_RESULT_SOURCE_RELEASE.json",
    "artifact_preflight_unit_test_sha256": ROOT / "scripts/test_reserved1664_artifact_preflight.py",
    "cleanup_finalizer_unit_test_sha256": ROOT / "scripts/test_reserved1664_cleanup_finalizer.py",
    "environment_prepare_sha256": BASE / "prepare_reserved1664_full_gate.sh",
    "ioctl_protocol_unit_test_sha256": ROOT / "scripts/test_reserved1664_ioctl_protocol.py",
    "first_board_failure_result_sha256": BASE / "M17_RESERVED1664_MAPPING_FAILURE_RESULT.json",
    "ioctl_protocol_result_sha256": BASE / "M17_RESERVED1664_IOCTL_PROTOCOL_RESULT.json",
    "model_hash_cma_probe_script_sha256": ROOT / "scripts/m17_probe_model_hash_cma.sh",
    "model_hash_cma_probe_result_sha256": BASE / "M17_MODEL_HASH_CMA_PROBE_RESULT.json",
    "second_board_failure_result_sha256": BASE / "M17_RESERVED1664_MEMORY_PREFLIGHT_FAILURE_RESULT.json",
    "source_cache_release_unit_test_sha256": ROOT / "scripts/test_resident_source_cache_release.py",
    "source_cache_release_result_sha256": BASE / "M17_RESERVED1664_SOURCE_CACHE_RELEASE_RESULT.json",
    "warmup_gate_unit_test_sha256": ROOT / "scripts/test_resident_e2e_warmup_gate.py",
    "authorized_cycle_arm_sha256": BASE / "arm_reserved1664_authorized_cycle.sh",
    "authorized_cycle_runner_sha256": BASE / "run_reserved1664_authorized_cycle.sh",
    "authorized_cycle_unit_sha256": BASE / "tellme-reserved1664-cycle.service",
    "authorized_cleanup_runner_sha256": BASE / "run_reserved1664_authorized_cleanup.sh",
    "authorized_cleanup_unit_sha256": BASE / "tellme-reserved1664-cleanup.service",
    "authorized_cycle_audit_sha256": ROOT / "scripts/test_reserved1664_authorized_cycle.py",
    "authorized_cycle_plan_sha256": BASE / "M17_RESERVED1664_AUTHORIZED_CYCLE_PLAN.json",
}


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def main() -> int:
    artifacts = json.loads(PLAN.read_text(encoding="utf-8"))["artifacts"]
    failures = []
    for key, path in PATHS.items():
        expected = artifacts.get(key)
        actual = sha256(path) if path.is_file() else None
        if actual != expected:
            failures.append({"key": key, "path": str(path), "expected": expected, "actual": actual})
    if failures:
        print(json.dumps(failures, indent=2))
        print("QWEN_RESERVED1664_PLAN_ARTIFACT_AUDIT_FAIL")
        return 1
    print(f"QWEN_RESERVED1664_PLAN_ARTIFACT_AUDIT_PASS count={len(PATHS)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
