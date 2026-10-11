from __future__ import annotations

import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CONFIG = ROOT / "bact" / "bact_v2_protocol.json"
PROTOCOL = ROOT / "M312_BACT_EVALUATION_PROTOCOL_V2.md"
M306 = ROOT / "deployment" / "mage_vl4b" / "M306_FOUR_BASELINE_PREDICTION_GEOMETRY_RESULT.json"
M308_SEAL = ROOT / "deployment" / "mage_vl4b" / "M308_BACT_HELDOUT_EVALUATION_SEAL.json"
M309 = ROOT / "deployment" / "mage_vl4b" / "M309_BACT_FINAL_EVIDENCE_PACK_RESULT.json"
M311 = ROOT / "deployment" / "mage_vl4b" / "M311_BACT_COMPLETION_AUDIT_RESULT.json"
OUTPUT = ROOT / "deployment" / "mage_vl4b" / "M312_BACT_EVALUATION_PROTOCOL_V2_RESULT.json"


EXPECTED_BASELINES = {
    "fixed_high_quality": ("high-284", 284, 9, 1394),
    "fixed_ratio_visual_pruning": ("ratio-164", 164, 6, 932),
    "token_count_aware": ("count-144", 144, 5, 778),
    "bact": ("bact-159", 159, 5, 778),
}


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def require(condition: bool, message: str) -> None:
    if not condition:
        raise RuntimeError(message)


def main() -> int:
    config = read_json(CONFIG)
    geometry = read_json(M306)
    old_seal = read_json(M308_SEAL)
    old_pack = read_json(M309)
    completion = read_json(M311)

    require(config["schema"] == "tellme-bact-v2-preregistered-protocol-v1", "schema mismatch")
    require(completion["status"] == "PASS_OBJECTIVE_COMPLETE_AT_HUMAN_REVIEWED_AI_PILOT_SCOPE", "M311 mismatch")
    require(sha256(M311) == config["historyPolicy"]["historicalCompletionAuditSha256"], "M311 hash mismatch")
    require(old_seal["status"] == "COMPLETE", "historical M308 seal is not complete")
    require(old_pack["status"] == "PASS_FINAL_PILOT_EVIDENCE_PACK", "historical M309 pack mismatch")
    require(config["historyPolicy"]["historicalPilotTestMayBeRetuned"] is False, "old test retune must be false")
    require(config["historyPolicy"]["historicalPilotTestMayBeReopened"] is False, "old test reopen must be false")

    for name, expected in EXPECTED_BASELINES.items():
        candidate_id, tokens, batches, calls = expected
        observed = config["baselines"][name]
        require((observed["candidateId"], observed["totalTokens"], observed["t32Batches"], observed["logicalCalls"]) == expected, f"protocol baseline mismatch: {name}")
        geom = geometry["candidates"][name]
        require(geom["candidateId"] == candidate_id, f"geometry candidate mismatch: {name}")
        require(geom["knifePromptTokens"] == tokens, f"geometry token mismatch: {name}")
        require(geom["t32BatchesPerProbe"] == batches, f"geometry batch mismatch: {name}")
        require(geom["logicalFpgaCallsPerProbe"] == calls, f"geometry call mismatch: {name}")

    primary = config["hypotheses"]["primary"]
    require(primary["comparison"] == ["bact", "token_count_aware"], "primary comparison mismatch")
    require(primary["expectedBatchesEach"] == 5 and primary["expectedLogicalCallsEach"] == 778, "primary cost mismatch")
    require(config["statistics"]["independentUnit"] == "source_video", "wrong statistical unit")
    require(config["statistics"]["pairedBootstrapReplicates"] == 5000, "bootstrap count mismatch")
    require(config["dataset"]["minimumIndependentSourceVideos"] >= 100, "dataset minimum too small")
    require(config["dataset"]["minimumControlledOrLicensedRealPublicVideos"] >= 80, "real/public minimum too small")
    require(config["dataset"]["maximumAiGeneratedVideos"] <= 40, "AI maximum too large")
    require(config["annotation"]["minimumIndependentSecondAnnotatorFraction"] >= 0.2, "second annotation too small")
    require(config["annotation"]["minimumCohenKappaKnife"] >= 0.8, "knife kappa too low")
    require(config["annotation"]["minimumCohenKappaAction"] >= 0.8, "action kappa too low")
    require(config["calibration"]["thresholdsUseHeldOutLabels"] is False, "held-out threshold leakage")
    require(config["calibration"]["semanticProxyWeightsUseHeldOutLabels"] is False, "held-out proxy leakage")
    require(config["predictionIntegrity"]["silentDeletionAllowed"] is False, "silent deletion enabled")
    require(config["heldOutSeal"]["openExactlyOnce"] is True, "one-shot seal disabled")
    require(config["heldOutSeal"]["writeOpenedSealBeforeReadingLabels"] is True, "OPENED seal order mismatch")
    require(config["selectorCandidateSpace"]["selectionUsesHeldOutLabels"] is False, "selector test leakage")

    result = {
        "date": "2026-09-03",
        "gate": "M312-BACT-V2-preregistered-evaluation-protocol",
        "status": "PASS_PROTOCOL_V2_FROZEN_DATA_COLLECTION_PENDING",
        "classification": "Pre-registered BACT-V2 quality-cost protocol and immutable historical boundary; no new dataset, label agreement, prediction, accuracy, board, power, real-time or external-validity result.",
        "protocol": str(PROTOCOL.relative_to(ROOT)).replace("\\", "/"),
        "protocolSha256": sha256(PROTOCOL),
        "machineContract": str(CONFIG.relative_to(ROOT)).replace("\\", "/"),
        "machineContractSha256": sha256(CONFIG),
        "sourceSha256": sha256(Path(__file__)),
        "upstream": {
            "m306GeometrySha256": sha256(M306),
            "historicalM308SealSha256": sha256(M308_SEAL),
            "historicalM309PackSha256": sha256(M309),
            "historicalM311AuditSha256": sha256(M311),
            "planningDocumentSha256": "d2652e081ade04690f37a68b404ebda1faec055513cc6271f0d5c6e7cbaccb07",
        },
        "primaryComparison": ["bact-159", "count-144"],
        "primaryCostIdentity": {"t32BatchesEach": 5, "logicalCallsEach": 778},
        "statistics": {"unit": "source_video", "pairedBootstrapReplicates": 5000, "confidenceLevel": 0.95},
        "datasetGate": {"minimumSources": 100, "targetSources": 120, "minimumRealControlledOrLicensedPublic": 80, "maximumAiGenerated": 40},
        "historicalPilotPreserved": True,
        "heldOutTestOpened": False,
        "newPredictionsRun": False,
        "boardExecutionRun": False,
        "activeM254M256Changed": False,
        "bootDtbCmaPartitionsChanged": False,
        "stableRollbackPreserved": True,
        "nextGate": "Implement and test the label-blind BACT-V2 discrete candidate selector over B4/B5/B6 before collecting or opening any new held-out labels.",
    }
    OUTPUT.write_text(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(f"M312_BACT_V2_PROTOCOL_PASS protocol_sha256={result['protocolSha256']} contract_sha256={result['machineContractSha256']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
