#!/usr/bin/env python3
"""Deterministic evidence gate for the outcome-blind BACT-V2 selector."""

from __future__ import annotations

import argparse
import hashlib
import inspect
import json
import os
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from bact.selector_v2 import (
    ALLOWED_FAMILIES,
    ProxyWeights,
    T32CostIdentity,
    audit_all_candidates,
    candidate_from_mapping,
    select_bact_v2,
    validate_candidate_space,
)


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def canonical_bytes(value: object) -> bytes:
    return (json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n").encode("utf-8")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--workspace", type=Path, required=True)
    parser.add_argument("--result", type=Path, required=True)
    args = parser.parse_args()
    workspace = args.workspace.resolve()
    config_path = workspace / "bact/bact_v2_selector_config.json"
    source_path = workspace / "bact/selector_v2.py"
    config = json.loads(config_path.read_text(encoding="utf-8"))

    hardware = config["hardware"]
    cost = T32CostIdentity(
        token_granularity=int(hardware["tokenGranularity"]),
        language_calls_per_batch=int(hardware["languageCallsPerBatch"]),
        fixed_calls=int(hardware["fixedCalls"]),
    )
    weights = ProxyWeights(**{key: float(value) for key, value in config["proxyWeights"].items()})
    candidates = [candidate_from_mapping(raw) for raw in config["candidates"]]
    validate_candidate_space(candidates, config["bandRanges"])
    selection = select_bact_v2(
        candidates,
        weights,
        float(config["maximumSemanticLossProxy"]),
        cost,
    )

    boundary_cases = {}
    for center in (128, 160, 192):
        values = []
        for tokens in (center - 1, center, center + 1):
            values.append(
                {"tokens": tokens, "batches": cost.batches(tokens), "logical_calls": cost.logical_calls(tokens)}
            )
        boundary_cases[str(center)] = values
    assert boundary_cases["128"] == [
        {"tokens": 127, "batches": 4, "logical_calls": 624},
        {"tokens": 128, "batches": 4, "logical_calls": 624},
        {"tokens": 129, "batches": 5, "logical_calls": 778},
    ]
    assert boundary_cases["160"][2]["logical_calls"] == 932
    assert boundary_cases["192"][2]["logical_calls"] == 1086

    negative_case = {
        "from_tokens": 159,
        "to_tokens": 130,
        "tokens_removed": 29,
        "from_batches": cost.batches(159),
        "to_batches": cost.batches(130),
        "from_calls": cost.logical_calls(159),
        "to_calls": cost.logical_calls(130),
    }
    negative_case["additional_hardware_batch_benefit"] = (
        negative_case["from_calls"] - negative_case["to_calls"]
    )
    assert negative_case["additional_hardware_batch_benefit"] == 0

    positive_case = {
        "from_tokens": 164,
        "to_tokens": 159,
        "tokens_removed": 5,
        "from_batches": cost.batches(164),
        "to_batches": cost.batches(159),
        "from_calls": cost.logical_calls(164),
        "to_calls": cost.logical_calls(159),
    }
    positive_case["removed_batches"] = positive_case["from_batches"] - positive_case["to_batches"]
    positive_case["removed_logical_calls"] = positive_case["from_calls"] - positive_case["to_calls"]
    assert positive_case["removed_batches"] == 1
    assert positive_case["removed_logical_calls"] == 154

    # Fail closed against outcome leakage and semantic filename hints.
    probe = dict(config["candidates"][0])
    leakage_rejections = {}
    for forbidden_key in ("human_label", "held_out_score", "filename_hint", "test_accuracy"):
        poisoned = dict(probe)
        poisoned[forbidden_key] = "must-not-be-read"
        try:
            candidate_from_mapping(poisoned)
        except ValueError as exc:
            leakage_rejections[forbidden_key] = str(exc)
        else:
            raise AssertionError(f"forbidden field accepted: {forbidden_key}")

    signature_names = {
        parameter.name.lower()
        for parameter in inspect.signature(select_bact_v2).parameters.values()
    }
    assert not any(
        forbidden in name
        for name in signature_names
        for forbidden in ("label", "heldout", "held_out", "test", "filename")
    )
    assert selection.candidate.candidate_id == "bact-159"
    assert selection.batches == 5 and selection.logical_calls == 778
    assert {candidate.adjustment_family for candidate in candidates} == ALLOWED_FAMILIES

    first_audit = audit_all_candidates(candidates, weights, cost)
    second = select_bact_v2(candidates, weights, float(config["maximumSemanticLossProxy"]), cost)
    deterministic = canonical_bytes(selection.to_dict()) == canonical_bytes(second.to_dict())
    assert deterministic

    result = {
        "date": "2026-09-03",
        "gate": "M313-BACT-V2-outcome-blind-discrete-selector",
        "status": "PASS_EXECUTABLE_SELECTOR_AND_BOUNDARY_CONTRACT",
        "classification": (
            "Executable outcome-blind BACT-V2 selector and exact T32 logical-call contract. Proxy values are "
            "a frozen calibration/inference-time fixture, not accuracy, latency, power or generalization evidence."
        ),
        "hardware_identity": {
            "build_id": hardware["buildId"],
            "kernel": hardware["kernel"],
            "formula": "154 * ceil(total_tokens / 32) + 8",
            "bitstream_changed": False,
        },
        "selection_rule": "minimize lexicographically (batches, D, -N) subject to D <= delta",
        "proxy_weights": config["proxyWeights"],
        "maximum_semantic_loss_proxy": config["maximumSemanticLossProxy"],
        "candidate_count": len(candidates),
        "candidate_audit": first_audit,
        "selected": selection.to_dict(),
        "boundary_cases": boundary_cases,
        "negative_same_plateau_case": negative_case,
        "positive_cross_boundary_case": positive_case,
        "leakage_contract": {
            "runtime_signature_parameters": sorted(signature_names),
            "rejected_fields": leakage_rejections,
            "human_outcomes_read": False,
            "historical_test_statistics_read": False,
            "filename_hints_read": False,
        },
        "deterministic_rerun": deterministic,
        "files": {
            "source": {"path": "bact/selector_v2.py", "sha256": sha256(source_path)},
            "config": {"path": "bact/bact_v2_selector_config.json", "sha256": sha256(config_path)},
            "gate": {
                "path": "scripts/m313_gate_bact_v2_selector.py",
                "sha256": sha256(Path(__file__).resolve()),
            },
        },
        "allowed_claim": (
            "Under the frozen proxy fixture, BACT-V2 automatically selects bact-159; it retains 15 more tokens "
            "than count-144 at the same exact 5-batch/778-call identity and crosses one batch/154 calls from ratio-164."
        ),
        "quality_superiority_claim_allowed": False,
        "new_board_run": False,
        "active_board_service_changed": False,
        "boot_dtb_cma_partitions_changed": False,
        "stable_rollback_preserved": True,
        "next_gate": "M314 hash-bind unchanged T32 geometry to existing KV260 boundary evidence; do not repeat 27 points.",
    }
    args.result.parent.mkdir(parents=True, exist_ok=True)
    partial = args.result.with_suffix(args.result.suffix + ".partial")
    partial.write_bytes(canonical_bytes(result))
    os.replace(partial, args.result)
    print(
        "M313_BACT_V2_SELECTOR_PASS "
        f"selected={selection.candidate.candidate_id} tokens={selection.candidate.total_tokens} "
        f"batches={selection.batches} calls={selection.logical_calls} candidates={len(candidates)}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
