#!/usr/bin/env python3
"""Run the frozen accepted fixed-text E2E with M241 grouped GQA."""
from __future__ import annotations

import json
import sys
from pathlib import Path

import text_e2e_gate as accepted_gate
from m238_prefill_runtime import M238PrefillRuntime
from m241_video_language_runtime import causal_attention_grouped


_grouped_calls = 0


class M242FixedTextRuntime(M238PrefillRuntime):
    """Route the accepted fixed-text family API through the real M238 many-token path."""

    def language_family(self, layer, family, values):
        return self.language_family_many(layer, family, values)


def counted_grouped_attention(q, k, v):
    global _grouped_calls
    _grouped_calls += 1
    return causal_attention_grouped(q, k, v)


def result_path() -> Path:
    try:
        return Path(sys.argv[sys.argv.index("--result") + 1])
    except (ValueError, IndexError) as exc:
        raise RuntimeError("M242 requires an explicit --result path") from exc


def main() -> int:
    accepted_gate.M120BoardRuntime = M242FixedTextRuntime
    accepted_gate.attention = counted_grouped_attention
    target = result_path()
    rc = accepted_gate.main()
    result = json.loads(target.read_text(encoding="utf-8"))
    evidence = result.setdefault("evidence", {})
    evidence["prefill_attention"] = "m241-grouped-gqa-reference-rope"
    evidence["grouped_attention_calls"] = _grouped_calls
    evidence["expected_grouped_attention_calls"] = 36
    evidence["rope_cache_used"] = False
    passed = rc == 0 and result.get("status") == "PASS" and _grouped_calls == 36
    if not passed:
        result["status"] = "FAIL"
        result["m242_error"] = "grouped-GQA fixed-text structural gate failed"
    partial = target.with_name(target.name + ".m242.partial")
    partial.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    partial.replace(target)
    print("M242_GROUPED_GQA_FIXED_TEXT_INNER_PASS" if passed else "M242_GROUPED_GQA_FIXED_TEXT_INNER_FAIL")
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
