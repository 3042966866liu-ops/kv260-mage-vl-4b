#!/usr/bin/env python3
"""Deterministic contract test for the M297 BACT staircase model."""

from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts/m297_fit_bact_staircase_cost_model.py"
SOURCE = ROOT / "deployment/mage_vl4b/M294R3_COUNTERBALANCED_BOUNDARY_BOARD_RESULT_05.json"
OUTPUT = ROOT / "deployment/mage_vl4b/M297_BACT_STAIRCASE_COST_MODEL_RESULT.json"


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> int:
    command = [sys.executable, str(SCRIPT), "--source", str(SOURCE), "--output", str(OUTPUT)]
    subprocess.run(command, cwd=ROOT, check=True)
    first = digest(OUTPUT)
    subprocess.run(command, cwd=ROOT, check=True)
    second = digest(OUTPUT)
    if first != second:
        raise SystemExit("M297_DETERMINISM_FAIL")

    data = json.loads(OUTPUT.read_text(encoding="utf-8"))
    assert data["status"] == "PASS_REPRODUCIBLE_DESCRIPTIVE_MODEL_NOT_CAUSAL"
    assert data["sample_count"] == 27
    assert data["structural_cost_model"]["identity_passed_for_all_27_records"] is True
    assert data["claim_policy"]["structural_staircase_claim_allowed"] is True
    assert data["claim_policy"]["causal_speed_claim_allowed"] is False
    assert data["claim_policy"]["semantic_accuracy_claim_allowed"] is False
    assert data["claim_policy"]["real_time_claim_allowed"] is False
    assert all(row["step_exceeds_same_batch_mad"] for row in data["boundary_contrasts"])
    assert abs(data["cross_boundary_step_summary"]["median_ms"] - 20141.517876530997) < 1e-6
    assert data["empirical_latency_model"]["valid_prompt_token_range_inclusive"] == [127, 193]
    assert data["empirical_latency_model"]["extrapolation_allowed"] is False
    assert data["board_execution_run"] is False
    print(f"M297_BACT_STAIRCASE_COST_MODEL_TEST_PASS sha256={second}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
