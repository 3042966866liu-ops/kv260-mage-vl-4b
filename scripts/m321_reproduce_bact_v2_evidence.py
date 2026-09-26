#!/usr/bin/env python3
"""Read-only reproduction of frozen BACT-V2 selector, board cost and pilot quality."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from bact.evaluation import (  # noqa: E402
    BASELINE_IDS, _argmax_action, action_macro_f1, evaluate_four_baselines,
    index_predictions, index_verified_labels, knife_metrics,
)
from bact.selector_v2 import (  # noqa: E402
    ProxyWeights, T32CostIdentity, audit_all_candidates, candidate_from_mapping,
    select_bact_v2, validate_candidate_space,
)

SELECTOR_CONFIG = ROOT / "bact/bact_v2_selector_config.json"
SELECTOR = ROOT / "deployment/mage_vl4b/M313_BACT_V2_SELECTOR_RESULT.json"
BOUNDARY = ROOT / "deployment/mage_vl4b/M294R3_COUNTERBALANCED_BOUNDARY_BOARD_RESULT_05.json"
COST = ROOT / "deployment/mage_vl4b/M314_BACT_V2_BOARD_COST_BINDING_RESULT.json"
GEOMETRY = ROOT / "deployment/mage_vl4b/M306_FOUR_BASELINE_PREDICTION_GEOMETRY_RESULT.json"
LABELS = ROOT / "data/bact_target_scene/M304_HUMAN_REVIEW_LABELS.json"
PREDICTIONS = ROOT / "data/bact_target_scene/M307_FOUR_BASELINE_PREDICTIONS.json"
EVALUATION = ROOT / "deployment/mage_vl4b/M308_BACT_HELDOUT_EVALUATION_RESULT.json"
PAIRED = ROOT / "experiments/bact_v2_quality/paired_quality.json"


def read_json(path: Path) -> dict:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"JSON object expected: {path}")
    return value


def sha(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(8 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def require(condition: bool, message: str) -> None:
    if not condition:
        raise RuntimeError(message)


def require_hash(path: Path, expected: str, name: str) -> None:
    require(sha(path) == expected, f"{name} SHA-256 mismatch")


def reproduce_selector() -> dict:
    config, frozen = read_json(SELECTOR_CONFIG), read_json(SELECTOR)
    require(frozen["status"] == "PASS_EXECUTABLE_SELECTOR_AND_BOUNDARY_CONTRACT", "selector status drift")
    for name, info in frozen["files"].items():
        require_hash(ROOT / info["path"], info["sha256"], f"selector {name}")
    hardware = config["hardware"]
    cost = T32CostIdentity(
        token_granularity=int(hardware["tokenGranularity"]),
        language_calls_per_batch=int(hardware["languageCallsPerBatch"]),
        fixed_calls=int(hardware["fixedCalls"]),
    )
    weights = ProxyWeights(**{key: float(value) for key, value in config["proxyWeights"].items()})
    candidates = [candidate_from_mapping(value) for value in config["candidates"]]
    validate_candidate_space(candidates, config["bandRanges"])
    selected = select_bact_v2(candidates, weights, float(config["maximumSemanticLossProxy"]), cost)
    require(len(candidates) == frozen["candidate_count"] == 9, "nine-candidate count drift")
    require(selected.to_dict() == frozen["selected"], "selector output drift")
    require(audit_all_candidates(candidates, weights, cost) == frozen["candidate_audit"], "candidate audit drift")
    require(selected.candidate.candidate_id == "bact-159", "unexpected selected candidate")
    require(selected.batches == 5 and selected.logical_calls == 778, "selected cost drift")
    return {
        "status": "PASS",
        "candidate_count": len(candidates),
        "selected": selected.candidate.candidate_id,
        "tokens": selected.candidate.total_tokens,
        "batches": selected.batches,
        "logical_calls": selected.logical_calls,
        "proxy_kind": "frozen fixture, not calibrated task accuracy",
        "config_sha256": sha(SELECTOR_CONFIG),
    }


def reproduce_cost() -> dict:
    frozen, board = read_json(COST), read_json(BOUNDARY)
    require(frozen["status"] == "PASS_EXISTING_BOARD_EVIDENCE_BOUND_NO_RERUN_REQUIRED", "cost status drift")
    for name, info in frozen["inputs"].items():
        require_hash(ROOT / info["path"], info["sha256"], f"cost {name}")
    require_hash(BOUNDARY, frozen["existing_board_evidence"]["sha256"], "27-point board record")
    require(board["completed_measurements"] == board["expected_measurements"] == 27, "board count drift")
    require(board["build_id"].lower() == frozen["identity"]["build_id"].lower(), "board Build ID drift")
    require(board["kernel"] == frozen["identity"]["kernel"], "board kernel drift")
    grouped: dict[int, int] = {}
    for record in board["records"]:
        tokens = int(record["prompt_tokens"])
        batches = math.ceil(tokens / 32)
        calls = 154 * batches + 8
        require(record["pass"] is True and record["finite"] is True, "board record failed")
        require(record["t32_batches"] == batches, "board batch drift")
        require(record["expected_logical_fpga_calls"] == calls, "board expected call drift")
        require(record["observed_logical_fpga_calls"] == calls, "board observed call drift")
        grouped[tokens] = grouped.get(tokens, 0) + 1
    require(set(grouped) == {127, 128, 129, 159, 160, 161, 191, 192, 193}, "board boundary points drift")
    require(all(count == 3 for count in grouped.values()), "board repetition count drift")
    baselines = frozen["baseline_cost_identities"]
    for name, expected in {"count-144": (144, 5, 778), "bact-159": (159, 5, 778), "ratio-164": (164, 6, 932)}.items():
        item = baselines[name]
        require((item["total_tokens"], item["t32_batches"], item["logical_calls"]) == expected, f"{name} cost drift")
    return {
        "status": "PASS",
        "build_id": board["build_id"],
        "measured_records": sum(grouped.values()),
        "unique_token_points": sorted(grouped),
        "same_batch": {"count-144": "5/778", "bact-159": "5/778"},
        "cross_boundary": {"ratio-164": "6/932", "bact-159": "5/778"},
        "board_record_sha256": sha(BOUNDARY),
        "new_board_runs": 0,
    }


def split_metrics(labels: dict, rows: dict, threshold: float, split: str) -> dict:
    ids = sorted(key for key, value in labels.items() if split == "all" or value["split"] == split)
    knife = knife_metrics(((labels[key]["knifePresent"], rows[key]["knifeScore"]) for key in ids), threshold)
    action = action_macro_f1(((labels[key]["action"], _argmax_action(rows[key]["actionLogits"])) for key in ids))
    balanced = (knife.recall + 1 - knife.false_alarm_rate) / 2
    return {
        "clips": len(ids),
        "knife_fn": knife.false_negative,
        "knife_fp": knife.false_positive,
        "action_macro_f1": action["macroF1"],
        "Q": (balanced + action["macroF1"]) / 2,
    }


def reproduce_quality() -> dict:
    frozen, paired = read_json(EVALUATION), read_json(PAIRED)
    for name, path, key in (
        ("labels", LABELS, "labelsSha256"),
        ("predictions", PREDICTIONS, "predictionsSha256"),
        ("geometry", GEOMETRY, "predictionGeometrySha256"),
    ):
        require_hash(path, frozen["identity"][key], f"historical {name}")
    labels_raw, predictions_raw = read_json(LABELS), read_json(PREDICTIONS)
    labels = index_verified_labels(labels_raw)
    predictions = index_predictions(predictions_raw, labels)
    computed = evaluate_four_baselines(labels_raw, predictions_raw, minimum_recall=0.9)
    require(set(computed) == set(BASELINE_IDS), "four baseline coverage drift")
    for name in BASELINE_IDS:
        require(computed[name] == frozen["metrics"]["baselines"][name]["primary"], f"{name} M308 primary drift")
    compared = {}
    four_baseline_test = {}
    for name in BASELINE_IDS:
        primary = computed[name]
        knife = primary["heldOutTest"]["knife"]
        macro_f1 = primary["heldOutTest"]["action"]["macroF1"]
        balanced = (knife["recall"] + 1 - knife["false_alarm_rate"]) / 2
        four_baseline_test[name] = {
            "candidate_id": BASELINE_IDS[name],
            "calibration_threshold": primary["thresholdFreeze"]["threshold"],
            "knife_fn": knife["false_negative"],
            "knife_fp": knife["false_positive"],
            "action_macro_f1": macro_f1,
            "Q": (balanced + macro_f1) / 2,
        }
    for name in ("bact", "token_count_aware"):
        threshold = computed[name]["thresholdFreeze"]["threshold"]
        compared[name] = {
            split: split_metrics(labels, predictions[name], threshold, split)
            for split in ("all", "test")
        }
        for split in ("all", "test"):
            old = paired["metrics"][name][split]
            new = compared[name][split]
            require(new["knife_fn"] == old["knife"]["false_negative"], f"{name}/{split} FN drift")
            require(new["knife_fp"] == old["knife"]["false_positive"], f"{name}/{split} FP drift")
            require(math.isclose(new["Q"], old["Q"], abs_tol=1e-12), f"{name}/{split} Q drift")
    require(len(labels) == 12, "historical pilot count drift")
    require(all(predictions["bact"][key]["actionLogits"] == predictions["token_count_aware"][key]["actionLogits"] for key in labels), "action logits mismatch")
    require(math.isclose(compared["bact"]["test"]["Q"], compared["token_count_aware"]["test"]["Q"], abs_tol=1e-12), "historical test tie drift")
    return {
        "status": "PASS_RETROSPECTIVE_ONLY",
        "historically_seen_clips": len(labels),
        "four_baseline_test": four_baseline_test,
        "four_baselines_reproduced": sorted(BASELINE_IDS),
        "paired": compared,
        "independent_quality_advantage_proven": False,
        "new_model_forwards": 0,
        "predictions_sha256": sha(PREDICTIONS),
        "paired_result_sha256": sha(PAIRED),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--only", choices=("selector", "cost", "quality", "all"), default="all")
    parser.add_argument("--output", type=Path, help="optional new JSON file; existing exact result is verified, never overwritten")
    args = parser.parse_args()
    result = {
        "schema": "tellme-bact-v2-read-only-reproduction-v1",
        "original_artifacts_modified": False,
    }
    if args.only in ("selector", "all"):
        result["selector"] = reproduce_selector()
    if args.only in ("cost", "all"):
        result["board_cost"] = reproduce_cost()
    if args.only in ("quality", "all"):
        result["pilot_quality"] = reproduce_quality()
    data = (json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True) + "\n").encode("utf-8")
    if args.output:
        output = args.output.resolve()
        if output.exists():
            require(output.read_bytes() == data, "existing reproduction output differs; refusing overwrite")
        else:
            output.parent.mkdir(parents=True, exist_ok=True)
            with output.open("xb") as stream:
                stream.write(data)
    details = {
        "selector": "selected=bact-159 candidates=9",
        "cost": "board_records=27 count144=5/778 bact159=5/778 ratio164=6/932",
        "quality": "baselines=4 old_clips=12 historical_test_advantage=false",
        "all": "selected=bact-159 candidates=9 board_records=27 baselines=4 old_clips=12 historical_test_advantage=false",
    }
    print(f"M321_BACT_V2_REPRODUCE_{args.only.upper()}_PASS {details[args.only]}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
