#!/usr/bin/env python3
"""Exact 64 MiB visual W4 component cache selected by M261's offline scan."""

from __future__ import annotations

import json
from pathlib import Path

import m222_vectorized_w4_runtime as _m222v
from m259_variable_vision_runtime import M259VariableFramePSVisionRuntime
from m260_cached_w4_runtime import M260CachedCodeFourPortW4Store


POLICY_PATH = Path(__file__).with_name("M261_CACHE_POLICY.json")
POLICY = json.loads(POLICY_PATH.read_text(encoding="utf-8"))
CACHE_NAMES = frozenset(POLICY["selected_names"])
EXPECTED_CACHE_BYTES = int(POLICY["expected_used_bytes"])
EXPECTED_CACHE_ENTRIES = int(POLICY["expected_cached_entries"])
if len(CACHE_NAMES) != EXPECTED_CACHE_ENTRIES:
    raise RuntimeError("M261 policy contains duplicate or missing cache names")


class M261BudgetedFourPortW4Store(M260CachedCodeFourPortW4Store):
    """Cache the selected exact components and bypass all other records."""

    def __init__(self, root):
        super().__init__(root)
        missing = CACHE_NAMES.difference(self.entries)
        if missing:
            raise RuntimeError(f"M261 policy entries missing from layout: {sorted(missing)}")
        self.uncached_decode_calls = 0

    def decode(self, name: str):
        if name not in CACHE_NAMES:
            self.uncached_decode_calls += 1
            return _m222v.M222VectorizedFourPortW4Store.decode(self, name)
        result = super().decode(name)
        if self.cache_bytes > EXPECTED_CACHE_BYTES:
            raise RuntimeError(
                f"M261 cache overflow: {self.cache_bytes}/{EXPECTED_CACHE_BYTES}"
            )
        return result

    def evidence(self) -> dict:
        value = super().evidence()
        value.update({
            "decoder": "M261-exact-bounded-packed-code-cache-v1",
            "policy_budget_mib": int(POLICY["budget_mib"]),
            "policy_expected_cache_bytes": EXPECTED_CACHE_BYTES,
            "policy_expected_cache_entries": EXPECTED_CACHE_ENTRIES,
            "uncached_decode_calls": self.uncached_decode_calls,
            "cache_within_budget": self.cache_bytes <= EXPECTED_CACHE_BYTES,
        })
        return value


class M261BudgetedVariableFramePSVisionRuntime(M259VariableFramePSVisionRuntime):
    """M259 math with an exact, bounded, process-local cache."""

    def __init__(self, *args, **kwargs):
        original = _m222v.M222VectorizedFourPortW4Store
        _m222v.M222VectorizedFourPortW4Store = M261BudgetedFourPortW4Store
        try:
            super().__init__(*args, **kwargs)
        finally:
            _m222v.M222VectorizedFourPortW4Store = original

    def decoder_evidence(self) -> dict:
        return self.store.evidence()
