#!/usr/bin/env python3
"""Host-only behavioral gate for M20 resident sequential Prefill."""

from __future__ import annotations

import sys
from pathlib import Path
from types import SimpleNamespace

import numpy as np


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "deployment/qwen25_3b_directddr_chain/runtime"))
sys.path.insert(0, str(ROOT / "deployment/qwen25_3b_no_final_forward/runtime"))

from resident_sequential_prefill_runtime import (  # noqa: E402
    EXPECTED_PREFILL_CALLS,
    EXPECTED_PREFILL_MACROS,
    PREFILL_EXECUTION_MODE,
    QwenResidentSequentialPrefillRuntime,
)


class FakeEngine:
    def __init__(self) -> None:
        self.finished = 0
        self.reset_count = 0

    def finish_prefetch(self) -> None:
        self.finished += 1

    def reset_profile(self) -> None:
        self.reset_count += 1


def main() -> int:
    runtime = QwenResidentSequentialPrefillRuntime.__new__(
        QwenResidentSequentialPrefillRuntime
    )
    runtime._engine_stage = "decode"
    runtime.engine = FakeEngine()
    runtime.max_seq_len = 16
    runtime.position = 0
    runtime._prefill_logits_ready = False
    calls: list[tuple[int, bool]] = []

    def fake_forward(token_id: int, compute_logits: bool = True):
        calls.append((token_id, compute_logits))
        runtime.position += 1
        if compute_logits:
            return np.asarray([1.0, 3.0, 2.0], dtype=np.float32)
        return None

    runtime.forward_token = fake_forward
    logits = runtime.prefill_tokens([11, 12, 13])
    assert calls == [(11, False), (12, False), (13, True)]
    assert runtime.position == 3
    assert runtime._prefill_logits_ready is True
    assert np.array_equal(logits, np.asarray([1.0, 3.0, 2.0], np.float32))
    passed = runtime._lm_head(logits)
    assert runtime._prefill_logits_ready is False
    assert passed is logits

    reset_runtime = QwenResidentSequentialPrefillRuntime.__new__(
        QwenResidentSequentialPrefillRuntime
    )
    reset_runtime._engine_stage = "decode"
    reset_runtime.engine = FakeEngine()
    reset_runtime.position = 9
    reset_runtime.lm_head_ms = 1.0
    reset_runtime.lm_head_rescore_ms = 2.0
    reset_runtime.lm_head_calls = 3
    reset_runtime._prefill_logits_ready = True
    reset_runtime._meminfo_kib = lambda name: {
        "CmaFree": 522_512,
        "Cached": 100_000,
        "MemAvailable": 1_172_064,
    }[name]
    # reset() checks the concrete engine class in production.  Exercise the
    # memory gate separately with a lightweight host stub.
    memory = reset_runtime._no_source_prefill_memory_gate()
    assert memory["status"] == "PASS"
    assert memory["method"] == "resident-directddr-no-prefill-source-mmap"
    assert memory["source_bytes"] == 0
    assert memory["prefill_execution_mode"] == PREFILL_EXECUTION_MODE

    assert EXPECTED_PREFILL_CALLS == 6_341
    assert EXPECTED_PREFILL_MACROS == 239_044_096
    assert 7 * (36 * 4 + 5) == 1_043
    assert 7 * (36 * 150_528 + 607_744) == 42_187_264

    low = QwenResidentSequentialPrefillRuntime.__new__(
        QwenResidentSequentialPrefillRuntime
    )
    low._meminfo_kib = lambda name: {
        "CmaFree": 131_071,
        "Cached": 100_000,
        "MemAvailable": 1_000_000,
    }[name]
    try:
        low._no_source_prefill_memory_gate()
    except RuntimeError as exc:
        assert "insufficient CMA" in str(exc)
    else:
        raise AssertionError("M20 accepted less than the 128 MiB CMA floor")

    print("QWEN_M20_RESIDENT_SEQUENTIAL_PREFILL_UNIT_PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
