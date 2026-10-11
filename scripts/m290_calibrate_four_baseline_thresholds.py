#!/usr/bin/env python3
"""Calibrate preliminary per-baseline knife thresholds from the M289 screen."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from bact.calibration import calibrate_binary_threshold


M289_SHA256 = "661cf447500ca920d9999dafab6f7291a99f04d8bf1143e9318586b7d1d59d40"


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def canonical_sha256(value: dict) -> str:
    payload = json.dumps(value, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--workspace", type=Path, required=True)
    parser.add_argument("--result", type=Path, required=True)
    args = parser.parse_args()
    workspace = args.workspace.resolve()
    source = workspace / "deployment/mage_vl4b/M289_M120_A8_FOUR_BASELINE_SCREEN_RESULT.json"
    if sha256(source) != M289_SHA256:
        raise RuntimeError("M290 M289 predecessor identity mismatch")
    predecessor = json.loads(source.read_text(encoding="utf-8"))
    if predecessor.get("status") != "FAIL_FOUR_BASELINE_SMALL_SCREEN":
        raise RuntimeError("M290 expects the preserved uncalibrated M289 FAIL")

    thresholds = {}
    for baseline in predecessor["baselines"]:
        records = [
            {"score": float(record["margin_yes_minus_no"]), "label": int(record["expected"])}
            for record in baseline["records"]
        ]
        selected = calibrate_binary_threshold(
            records,
            split="calibration",
            minimum_recall=1.0,
            maximum_false_alarm_rate=0.0,
        )
        thresholds[baseline["baseline"]] = selected.to_dict()

    leakage_rejected = False
    try:
        calibrate_binary_threshold(
            [{"score": -1.0, "label": 0}, {"score": 1.0, "label": 1}],
            split="test",
            minimum_recall=1.0,
            maximum_false_alarm_rate=0.0,
        )
    except ValueError as error:
        leakage_rejected = "calibration split" in str(error)
    if not leakage_rejected:
        raise RuntimeError("M290 test-label threshold fitting was not rejected")

    frozen_config = {
        "schema": "tellme-bact-knife-thresholds-v1",
        "source": "M289 four-sample calibration screen",
        "minimum_recall": 1.0,
        "maximum_false_alarm_rate": 0.0,
        "thresholds": {name: value["threshold"] for name, value in sorted(thresholds.items())},
    }
    result = {
        "date": "2026-09-02",
        "gate": "M290-preliminary-four-baseline-threshold-calibration",
        "status": "PASS_PRELIMINARY_CALIBRATION_CONTRACT",
        "classification": (
            "Deterministic per-baseline threshold fitting on the four M289 screening examples only. "
            "These thresholds prove calibration mechanics and rescue the M289 argmax mismatch on the same "
            "screen, but are not target-scene production thresholds or held-out accuracy evidence."
        ),
        "m289_status_preserved": predecessor["status"],
        "m289_sha256": sha256(source),
        "selection_rule": (
            "On calibration only: require frozen recall/FAR constraints; then maximize recall, minimize FAR, "
            "maximize accuracy and minimum score clearance."
        ),
        "thresholds": thresholds,
        "frozen_config": frozen_config,
        "frozen_config_canonical_sha256": canonical_sha256(frozen_config),
        "test_split_calibration_rejected": leakage_rejected,
        "thresholds_are_final": False,
        "held_out_test_run": False,
        "semantic_accuracy_passed": False,
        "active_board_service_changed": False,
        "boot_dtb_cma_partitions_changed": False,
        "stable_rollback_preserved": True,
        "next_gate": (
            "Replace this four-sample screen with a source-video-disjoint real calibration set, refreeze all "
            "four threshold values and configuration IDs, then run the held-out test evaluator exactly once."
        ),
    }
    args.result.parent.mkdir(parents=True, exist_ok=True)
    partial = args.result.with_suffix(args.result.suffix + ".partial")
    partial.write_text(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    os.replace(partial, args.result)
    print("M290_THRESHOLD_CALIBRATION_PASS " + " ".join(f"{k}={v['threshold']}" for k, v in thresholds.items()))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
