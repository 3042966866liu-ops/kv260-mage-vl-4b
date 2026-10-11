#!/usr/bin/env python3
"""Unit-test the resident source-weight cache release without FPGA hardware."""

from __future__ import annotations

import sys
import tempfile
from types import SimpleNamespace
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "deployment/qwen25_3b_directddr_chain/runtime"))
sys.path.insert(0, str(ROOT / "deployment/qwen25_3b_no_final_forward/runtime"))

import resident_chain_runtime as runtime_module  # noqa: E402
from resident_chain_runtime import QwenResidentRuntime, ResidentWeightStore  # noqa: E402


class FakeMapping:
    def __init__(self) -> None:
        self.advice = []
        self.closed = False

    def madvise(self, advice: int) -> None:
        self.advice.append(advice)

    def close(self) -> None:
        self.closed = True


class FakeArray:
    def __init__(self, mapping: FakeMapping) -> None:
        self._mmap = mapping


def make_store(directory: Path, *, cma_after_kib: int) -> tuple[ResidentWeightStore, list[FakeMapping]]:
    linear = directory / "linear.mgs"
    lm_head = directory / "lm_head.mgs"
    linear.write_bytes(b"l" * 4096)
    lm_head.write_bytes(b"h" * 2048)
    mappings = [FakeMapping(), FakeMapping()]
    store = ResidentWeightStore.__new__(ResidentWeightStore)
    store.linear_weight_path = linear
    store.lm_head_weight_path = lm_head
    store.weights = FakeArray(mappings[0])
    store.lm_head_weights = FakeArray(mappings[1])
    values = {
        "CmaFree": iter((64 * 1024, cma_after_kib)),
        "Cached": iter((2_000_000, 100_000)),
        "MemAvailable": iter((500_000, 2_000_000)),
    }
    store._meminfo_kib = lambda name: next(values[name])
    return store, mappings


def main() -> int:
    # Keep the fault-injection test portable on the Windows host.  Production
    # Linux must still supply these APIs; the test substitutes only their
    # side effects while using real temporary source files.
    runtime_module.os.POSIX_FADV_DONTNEED = 4
    runtime_module.os.posix_fadvise = lambda *_args: None
    runtime_module.mmap.MADV_DONTNEED = 4

    with tempfile.TemporaryDirectory(prefix="tellme-cache-release-") as raw:
        root = Path(raw)
        pass_root = root / "pass"
        pass_root.mkdir()
        passed_store, passed_mappings = make_store(
            pass_root, cma_after_kib=256 * 1024
        )
        result = passed_store._release_source_weight_page_cache()
        assert result["status"] == "PASS"
        assert result["source_bytes"] == 6144
        assert result["cma_recovered_kib"] == 192 * 1024
        assert passed_store.weights is None
        assert passed_store.lm_head_weights is None
        assert all(mapping.advice and mapping.closed for mapping in passed_mappings)

        fail_root = root / "fail"
        fail_root.mkdir()
        failed_store, _ = make_store(fail_root, cma_after_kib=127 * 1024)
        try:
            failed_store._release_source_weight_page_cache()
        except RuntimeError as exc:
            assert "insufficient CMA" in str(exc)
        else:
            raise AssertionError("cache release accepted less than the 128 MiB gate")

        prefill_root = root / "prefill-pass"
        (prefill_root / "model").mkdir(parents=True)
        (prefill_root / "lm_head").mkdir()
        linear = prefill_root / "model" / "linear.mgs"
        lm_head = prefill_root / "lm_head" / "test_lm_head_w4g64.mgs"
        linear.write_bytes(b"p" * 8192)
        lm_head.write_bytes(b"m" * 4096)
        (prefill_root / "lm_head" / "test_lm_head_w4g64.json").write_text("{}")
        prefill_mappings = [FakeMapping(), FakeMapping()]
        engine = SimpleNamespace(
            root=prefill_root,
            index={"linear_file": {"path": "linear.mgs"}},
            weights=FakeArray(prefill_mappings[0]),
            lm_head_weights=FakeArray(prefill_mappings[1]),
        )
        runtime = QwenResidentRuntime.__new__(QwenResidentRuntime)
        prefill_values = {
            "CmaFree": iter((70 * 1024, 300 * 1024)),
            "Cached": iter((1_600_000, 120_000)),
            "MemAvailable": iter((400_000, 1_700_000)),
        }
        runtime._meminfo_kib = lambda name: next(prefill_values[name])
        prefill_result = runtime._release_prefill_source_page_cache(engine)
        assert prefill_result["status"] == "PASS"
        assert prefill_result["source_bytes"] == 12_288
        assert prefill_result["cma_recovered_kib"] == 230 * 1024
        assert engine.weights is None and engine.lm_head_weights is None
        assert all(mapping.advice and mapping.closed for mapping in prefill_mappings)

        prefill_fail_root = root / "prefill-fail"
        (prefill_fail_root / "model").mkdir(parents=True)
        (prefill_fail_root / "lm_head").mkdir()
        (prefill_fail_root / "model" / "linear.mgs").write_bytes(b"x" * 4096)
        (prefill_fail_root / "lm_head" / "test_lm_head_w4g64.mgs").write_bytes(
            b"y" * 2048
        )
        (
            prefill_fail_root / "lm_head" / "test_lm_head_w4g64.json"
        ).write_text("{}")
        failed_engine = SimpleNamespace(
            root=prefill_fail_root,
            index={"linear_file": {"path": "linear.mgs"}},
            weights=FakeArray(FakeMapping()),
            lm_head_weights=FakeArray(FakeMapping()),
        )
        failed_runtime = QwenResidentRuntime.__new__(QwenResidentRuntime)
        failed_values = {
            "CmaFree": iter((70 * 1024, 120 * 1024)),
            "Cached": iter((1_600_000, 100_000)),
            "MemAvailable": iter((400_000, 1_700_000)),
        }
        failed_runtime._meminfo_kib = lambda name: next(failed_values[name])
        try:
            failed_runtime._release_prefill_source_page_cache(failed_engine)
        except RuntimeError as exc:
            assert "per-request Prefill cache release left insufficient CMA" in str(exc)
        else:
            raise AssertionError("per-request release accepted less than 128 MiB CMA")

    print("QWEN_RESIDENT_SOURCE_AND_PREFILL_CACHE_RELEASE_UNIT_PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
