#!/usr/bin/env python3
"""Contract tests for the sealed M309 final evidence pack."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from bact.dataset import ACTIONS
from bact.evaluation import BASELINE_IDS
from bact.robustness import evaluate_semantic_robustness


ROOT = Path(__file__).resolve().parents[1]
GENERATOR = Path(__file__).with_name("m309_generate_bact_final_evidence_pack.py")
REQUIRED = (
    "deployment/mage_vl4b/M288_BACT_SELECTOR_RESULT.json",
    "deployment/mage_vl4b/M294R3_COUNTERBALANCED_BOUNDARY_BOARD_RESULT_05.json",
    "deployment/mage_vl4b/M297_BACT_STAIRCASE_COST_MODEL_RESULT.json",
    "deployment/mage_vl4b/M300_BACT_RESOURCE_BINDING_RESULT.json",
    "deployment/mage_vl4b/M302_BACT_HARDWARE_ROBUSTNESS_RESULT.json",
    "deployment/mage_vl4b/M306_FOUR_BASELINE_PREDICTION_GEOMETRY_RESULT.json",
    "deployment/mage_vl4b/M307_FOUR_BASELINE_PREDICTION_COLLECTION_RESULT.json",
    "data/bact_target_scene/M307_FOUR_BASELINE_PREDICTIONS.json",
)


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write_json(path: Path, value: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def make_semantic_fixture() -> tuple[dict, dict]:
    clips = []
    action_rows = list(ACTIONS) + ["WORKING"]
    for split in ("calibration", "test"):
        for index, action in enumerate(action_rows):
            knife = index % 2 == 0
            conditions = {
                "lowLight": index in {0, 3},
                "occlusion": index in {1, 3},
                "smallKnife": index in {2, 4},
            }
            if conditions["smallKnife"]:
                knife = True
            clip_id = f"{split}-{index}"
            clips.append(
                {
                    "clipId": clip_id,
                    "split": split,
                    "sourceFilename": f"misleading-{clip_id}.mp4",
                    "videoSha256": hashlib.sha256(clip_id.encode()).hexdigest(),
                    "annotationStatus": "HUMAN_VERIFIED_COMPLETE_CLIP_CONSTANT",
                    "action": action,
                    "knifePresent": knife,
                    "actionConstant": True,
                    "knifeConstant": True,
                    "watchedComplete": True,
                    "annotator": "synthetic-contract",
                    "conditions": conditions,
                }
            )
    labels = {"schema": "tellme-bact-clip-constant-v1", "clips": clips}
    baselines = {}
    for baseline_index, (name, candidate_id) in enumerate(BASELINE_IDS.items()):
        rows = []
        for clip in clips:
            logits = {action: -3.0 for action in ACTIONS}
            logits[clip["action"]] = 3.0
            rows.append(
                {
                    "clipId": clip["clipId"],
                    "knifeScore": (2.0 if clip["knifePresent"] else -2.0) - baseline_index * 0.01,
                    "actionLogits": logits,
                }
            )
        baselines[name] = {"candidateId": candidate_id, "predictions": rows}
    predictions = {"schema": "tellme-bact-four-baseline-predictions-v1", "baselines": baselines}
    return labels, predictions


def run(workspace: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(GENERATOR), "--workspace", str(workspace)],
        text=True,
        capture_output=True,
        check=False,
    )


def main() -> int:
    with tempfile.TemporaryDirectory(prefix="m309-contract-") as directory:
        workspace = Path(directory)
        for relative in REQUIRED:
            destination = workspace / relative
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(ROOT / relative, destination)

        missing = run(workspace)
        if missing.returncode == 0 or (workspace / "BACT_FINAL_EVIDENCE_REPORT.md").exists():
            raise RuntimeError("M309 missing M308 evidence did not fail closed")

        labels, predictions = make_semantic_fixture()
        metrics = evaluate_semantic_robustness(labels, predictions)
        m307_path = workspace / "deployment/mage_vl4b/M307_FOUR_BASELINE_PREDICTION_COLLECTION_RESULT.json"
        m307 = json.loads(m307_path.read_text(encoding="utf-8"))
        evaluation_path = workspace / "deployment/mage_vl4b/M308_BACT_HELDOUT_EVALUATION_RESULT.json"
        evaluation = {
            "date": "2026-09-03",
            "status": "PASS_PILOT_HELDOUT_EVALUATION_SEALED",
            "identity": {
                "m307ResultSha256": sha(m307_path),
                "predictionsSha256": m307["predictionsSha256"],
                "baselineIds": dict(BASELINE_IDS),
            },
            "metrics": metrics,
            "calibrationOnlyThresholdSelection": True,
            "heldOutTestOpenedExactlyOnce": True,
            "formalPilotAccuracyAllowed": True,
            "realWorldExternalValidityClaimAllowed": False,
        }
        write_json(evaluation_path, evaluation)
        seal_path = workspace / "deployment/mage_vl4b/M308_BACT_HELDOUT_EVALUATION_SEAL.json"
        write_json(seal_path, {"status": "COMPLETE", "resultSha256": sha(evaluation_path)})

        first = run(workspace)
        if first.returncode != 0:
            raise RuntimeError(first.stdout + first.stderr)
        report_path = workspace / "BACT_FINAL_EVIDENCE_REPORT.md"
        claims_path = workspace / "BACT_APPLICATION_AND_RESUME_CLAIMS_FINAL.md"
        result_path = workspace / "deployment/mage_vl4b/M309_BACT_FINAL_EVIDENCE_PACK_RESULT.json"
        if not all(path.is_file() for path in (report_path, claims_path, result_path)):
            raise RuntimeError("M309 positive path did not create complete evidence pack")
        hashes = (sha(report_path), sha(claims_path), sha(result_path))

        repeated = run(workspace)
        if repeated.returncode != 0 or hashes != (sha(report_path), sha(claims_path), sha(result_path)):
            raise RuntimeError("M309 deterministic rerun mismatch")

        evaluation["heldOutTestOpenedExactlyOnce"] = False
        write_json(evaluation_path, evaluation)
        changed = run(workspace)
        if changed.returncode == 0 or hashes != (sha(report_path), sha(claims_path), sha(result_path)):
            raise RuntimeError("M309 changed/unsealed evidence was not rejected before overwrite")

    print(
        "M309_FINAL_PACK_CONTRACT_PASS "
        "missing_m308_blocked=true deterministic=true changed_evidence_rejected=true"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
