#!/usr/bin/env python3
"""Host-only M20 regression for the combined CPU and TTFT gate."""

from __future__ import annotations

import contextlib
import importlib.util
import io
import json
import sys
import tempfile
import types
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
GATE = (
    ROOT
    / "deployment"
    / "qwen25_3b_directddr_chain"
    / "runtime"
    / "m20_resident_full_e2e_gate_impl.py"
)
TOKENS = [100647, 30440, 110569, 64689, 99854, 31118, 9909, 37]
RESERVED_POOL = {
    "status": "PASS",
    "base": 0x808000000,
    "size_bytes": 0x68000000,
    "allocation_count": 435,
    "free_bytes": 8_384_512,
}
SOURCE_RELEASE = {
    "status": "PASS",
    "after_kib": {"CmaFree": 782_112},
    "minimum_cma_free_kib": 131_072,
}
PREFILL_RELEASE = {
    "status": "PASS",
    "after_kib": {"CmaFree": 760_000},
    "minimum_cma_free_kib": 131_072,
}
EMBEDDING_RESIDENCY = {
    "status": "PASS",
    "bytes": 622_329_856,
    "expected_sha256": "6be2a141e6242b71aaed7a16c3b4afb86cdb71ccf2ce40f43152715649a4cc82",
    "actual_sha256": "6be2a141e6242b71aaed7a16c3b4afb86cdb71ccf2ce40f43152715649a4cc82",
    "file_backed": False,
    "owns_memory": True,
    "c_contiguous": True,
    "minimum_cma_free_kib": 131_072,
    "minimum_memavailable_kib": 524_288,
    "after_kib": {"CmaFree": 600_000, "MemAvailable": 900_000},
}


class _Pool:
    def summary(self) -> dict:
        return dict(RESERVED_POOL)


class _Store:
    resident_weight_bytes = 1_735_704_576
    source_weight_page_cache_release = dict(SOURCE_RELEASE)


class FakeRuntime:
    corrupt_warmup = False
    measured_ttft_ms = 50_000.0

    def __init__(self, *_args, **_kwargs) -> None:
        self.store = _Store()
        self.resident_load_ms = 100.0
        self.hostbo_pool = None
        self.offline_ddr_pool = None
        self.reserved_ddr_pool = _Pool()
        self.tied_embedding_residency = dict(EMBEDDING_RESIDENCY)
        self.measured_index = 0

    def generate(self, _prompt: str, *, max_new_tokens: int, sampling: str):
        assert sampling == "argmax"
        prefill_calls = 6_341
        prefill_macros = 239_044_096
        if max_new_tokens == 2:
            token_ids = TOKENS[:2]
            if self.corrupt_warmup:
                token_ids = [TOKENS[0], 1]
            chain_calls = 149
            chain_macros = 6_026_752
            decode_ms = 2_000.0
        else:
            later_values = [735.0, 730.0, 723.0, 728.0]
            decode_ms = later_values[self.measured_index] * 7
            self.measured_index += 1
            token_ids = TOKENS
            chain_calls = 1_043
            chain_macros = 42_187_264
        proof = {
            "result": "PASS",
            "answer_token_ids_reencoded": token_ids,
            "prompt_tokens": 44,
            "generated_tokens": max_new_tokens,
            "ttft_ms": self.measured_ttft_ms,
            "decode_after_first_ms": decode_ms,
            "request_wall_ms": 1_000.0 + decode_ms,
            "prefill_overlay_load_ms": 0.0,
            "decode_overlay_load_ms": 0.0,
            "pl_kernel_calls": prefill_calls + chain_calls,
            "pl_macros": prefill_macros + chain_macros,
            "prefill_pl_kernel_calls": prefill_calls,
            "prefill_pl_macros": prefill_macros,
            "build_id": "0x51317A42",
            "prefill_build_id": "0x51317A42",
            "prefill_execution_mode": "resident-directddr-sequential-v1",
            "resident_weight_bytes": _Store.resident_weight_bytes,
            "runtime_optimization": "unit-test",
            "source_weight_page_cache_release": dict(SOURCE_RELEASE),
            "prefill_source_cache_release": dict(PREFILL_RELEASE),
            "tied_embedding_residency": dict(EMBEDDING_RESIDENCY),
            "profile_linear_calls": 0,
            "profile_lm_head_kernel_calls": 0,
            "prefill_cma_address_gate": {"status": "PASS"},
            "resident_cma_address_gate": {"status": "PASS"},
            "hostbo_pool": None,
            "offline_ddr_pool": None,
            "offline_ddr_weight_address_gate": None,
            "reserved_ddr_pool": dict(RESERVED_POOL),
            "reserved_ddr_weight_address_gate": {
                "status": "PASS",
                "buffer_count": 435,
            },
            "resident_low_cma_address_gate": {"status": "PASS"},
            "prefill_low_cma_address_gate": {"status": "PASS"},
        }
        return "现场" if max_new_tokens == 2 else "现场可编程门阵列（F", proof

    def close(self) -> None:
        pass


def _load_gate():
    fake_runtime_module = types.ModuleType("resident_chain_runtime")
    fake_runtime_module.QwenResidentRuntime = FakeRuntime
    previous = sys.modules.get("resident_chain_runtime")
    sys.modules["resident_chain_runtime"] = fake_runtime_module
    try:
        spec = importlib.util.spec_from_file_location("m20_resident_gate_test", GATE)
        assert spec is not None and spec.loader is not None
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        module.EXPECTED_CHAIN_CALLS = 1_043
        module.EXPECTED_CHAIN_MACROS = 42_187_264
        module.EXPECTED_WARMUP_CHAIN_CALLS = 149
        module.EXPECTED_WARMUP_CHAIN_MACROS = 6_026_752
        module.EXPECTED_PREFILL_BUILD_ID = "0x51317a42"
        module.EXPECTED_PREFILL_CALLS = 6_341
        module.EXPECTED_PREFILL_MACROS = 239_044_096
        module.EXPECTED_PREFILL_EXECUTION_MODE = "resident-directddr-sequential-v1"
        module.MILESTONE = "M20"
        module.GATE_NAME = "qwen25-3b-resident-sequential-prefill-full-e2e-cpu-gate"
        return module
    finally:
        if previous is None:
            del sys.modules["resident_chain_runtime"]
        else:
            sys.modules["resident_chain_runtime"] = previous


def _run(module, *, corrupt_warmup: bool, ttft_ms: float) -> tuple[int, list[dict], str]:
    FakeRuntime.corrupt_warmup = corrupt_warmup
    FakeRuntime.measured_ttft_ms = ttft_ms
    with tempfile.TemporaryDirectory() as temporary:
        saved_argv = sys.argv
        sys.argv = [
            str(GATE),
            "--stable-root",
            temporary,
            "--candidate-root",
            temporary,
            "--runs",
            "4",
        ]
        output = io.StringIO()
        try:
            with contextlib.redirect_stdout(output):
                rc = module.main()
        finally:
            sys.argv = saved_argv
    text = output.getvalue()
    payloads = []
    for line in text.splitlines():
        try:
            value = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(value, dict):
            payloads.append(value)
    return rc, payloads, text


def main() -> int:
    module = _load_gate()

    rc, payloads, text = _run(module, corrupt_warmup=False, ttft_ms=50_000.0)
    assert rc == 0, text
    final = next(item for item in payloads if item.get("gate") == "qwen25-3b-resident-sequential-prefill-full-e2e-cpu-gate")
    assert final["status"] == "PASS"
    assert final["warmup"]["status"] == "PASS"
    assert final["warmup"]["excluded_from_performance_statistics"] is True
    assert len(final["runs"]) == 4
    assert abs(final["fpga_average"]["later_token_ms"] - 729.0) < 1e-9
    assert final["measurement_method"]["warmup_runs"] == 1
    assert final["measurement_method"]["measured_runs"] == 4
    assert final["comparison"]["cpu_gate_pass"] is True
    assert final["comparison"]["mean_ttft_at_least_25_percent_lower"] is True
    assert "QWEN_M20_RESIDENT_FULL_E2E_CPU_AND_TTFT_PASS" in text

    rc, payloads, text = _run(module, corrupt_warmup=True, ttft_ms=50_000.0)
    assert rc == 1, text
    failure = next(item for item in payloads if item.get("gate") == "qwen25-3b-resident-sequential-prefill-full-e2e-cpu-gate")
    assert failure["status"] == "FAIL"
    assert failure["warmup"]["status"] == "FAIL"
    assert "QWEN_M20_RESIDENT_FULL_E2E_CPU_OR_TTFT_FAIL" in text

    rc, payloads, text = _run(module, corrupt_warmup=False, ttft_ms=60_000.0)
    assert rc == 1, text
    failure = next(item for item in payloads if item.get("gate") == "qwen25-3b-resident-sequential-prefill-full-e2e-cpu-gate")
    assert failure["comparison"]["cpu_gate_pass"] is True
    assert failure["comparison"]["mean_ttft_at_least_25_percent_lower"] is False
    assert failure["status"] == "FAIL"

    print("QWEN_M20_RESIDENT_CPU_AND_TTFT_GATE_UNIT_PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
