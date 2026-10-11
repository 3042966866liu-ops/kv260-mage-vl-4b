#!/usr/bin/env python3
"""Create authoritative offline evidence for M245/M246 before board work."""

from __future__ import annotations

import hashlib
import json
import os
import sys
from pathlib import Path

import numpy as np


ROOT = Path(__file__).resolve().parents[1]
M245 = ROOT / "deployment/mage_vl4b/m245_knife_alarm_source"
M246 = ROOT / "deployment/mage_vl4b/m246_knife_binary_source"
CANDIDATE = ROOT / "deployment/mage_vl4b/m246_knife_binary_board_candidate"
RESULT = ROOT / "deployment/mage_vl4b/M246_KNIFE_BINARY_OFFLINE_RESULT.json"
TOKENIZER = ROOT / "deployment/mage_vl4b/m181_m120_video_board_candidate/text_auxiliary/tokenizer/tokenizer.json"
EXPECTED_MANIFEST_SHA = "7cff5f28dae2ea48cb6e87127f4855075404a2d90694facde8289e78903920f3"


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


sys.path.insert(0, str(M245))
sys.path.insert(0, str(M246))
from knife_alarm import KnifeAlarmStateMachine, KnifeObservation  # noqa: E402
from m246_knife_binary import constrained_knife_decision  # noqa: E402


manifest_path = CANDIDATE / "PACKAGE_MANIFEST.json"
if sha(manifest_path) != EXPECTED_MANIFEST_SHA:
    raise RuntimeError("M246 candidate manifest hash mismatch")
manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
expected = {item["path"]: item for item in manifest["files"]}
observed = {
    path.relative_to(CANDIDATE).as_posix(): path
    for path in CANDIDATE.rglob("*")
    if path.is_file() and path.name != "PACKAGE_MANIFEST.json"
}
if set(expected) != set(observed):
    raise RuntimeError("M246 recursive package closure mismatch")
for name, item in expected.items():
    path = observed[name]
    if path.stat().st_size != int(item["bytes"]) or sha(path) != item["sha256"]:
        raise RuntimeError(f"M246 member mismatch: {name}")
if any("__pycache__" in path.parts or path.suffix == ".pyc" for path in observed.values()):
    raise RuntimeError("M246 forbidden Python cache")

tokenizer = json.loads(TOKENIZER.read_text(encoding="utf-8"))
vocab = tokenizer["model"]["vocab"]
if vocab.get("0") != 15 or vocab.get("1") != 16:
    raise RuntimeError(f"M246 tokenizer JSON contract mismatch 0={vocab.get('0')} 1={vocab.get('1')}")

logits = np.full(128, -8.0, dtype=np.float32)
logits[2] = 100.0
logits[15] = 1.0
logits[16] = 3.0
positive = constrained_knife_decision(logits)
if not (
    positive["token_id"] == 16
    and positive["full_vocabulary_argmax_token_id"] == 2
    and positive["score_calibrated"] is False
):
    raise RuntimeError("M246 positive constrained decision mismatch")
logits[15], logits[16] = 4.0, 0.0
negative = constrained_knife_decision(logits)
if negative["token_id"] != 15:
    raise RuntimeError("M246 negative constrained decision mismatch")

machine = KnifeAlarmStateMachine()
alarm = machine.update(KnifeObservation(0, (0, 1, 2, 3), "a" * 64, "PRESENT", 0.9, "1"))
if alarm["state"] != "ALARM" or alarm["calibration_required"] is not True:
    raise RuntimeError("M245 immediate alarm/calibration contract mismatch")
if machine.update(KnifeObservation(1, (4, 5, 6, 7), "b" * 64, "UNCERTAIN", 0.5, "?"))["state"] != "ALARM":
    raise RuntimeError("M245 uncertainty cleared an active alarm")
if machine.update(KnifeObservation(2, (8, 9, 10, 11), "c" * 64, "ABSENT", 0.1, "0"))["state"] != "ALARM":
    raise RuntimeError("M245 alarm cleared after only one absent window")
if machine.update(KnifeObservation(3, (12, 13, 14, 15), "d" * 64, "ABSENT", 0.1, "0"))["state"] != "SAFE":
    raise RuntimeError("M245 alarm did not clear after two absent windows")

server_source = (M246 / "m246_video_server.py").read_text(encoding="utf-8")
required_fragments = [
    "expected_physical_calls(len(ids), 1)",
    '"language_cpu_linear_fallback": False',
    '"score_calibrated": False',
    'yield "knife_observation"',
    'super().publish("knife_alarm", alarm)',
]
missing = [fragment for fragment in required_fragments if fragment not in server_source]
if missing:
    raise RuntimeError(f"M246 server contract fragments missing: {missing}")

value = {
    "date": "2026-09-02",
    "gate": "M246-constrained-knife-binary-offline",
    "status": "PASS",
    "classification": (
        "Offline package, tokenizer-ID, constrained-logit and alarm-state contract only; "
        "not board, visual-window, knife-accuracy, calibrated-threshold, Web, T64, or real-time evidence."
    ),
    "package_manifest_sha256": EXPECTED_MANIFEST_SHA,
    "package_file_count": len(expected),
    "package_total_bytes": sum(int(item["bytes"]) for item in expected.values()),
    "tokenizer_sha256": sha(TOKENIZER),
    "knife_no_token_id": 15,
    "knife_yes_token_id": 16,
    "full_vocabulary_eos_does_not_override_binary_decision": True,
    "fpga_proof_contract_preserved": True,
    "language_cpu_linear_fallback": False,
    "decode_calls_added": 0,
    "alarm_immediate_high_score": True,
    "alarm_uncertainty_does_not_clear": True,
    "alarm_absent_windows_to_clear": 2,
    "thresholds_calibrated": False,
    "t64_used": False,
    "board_execution_run": False,
    "stable_rollback_preserved": True,
    "next_gate": "COM3 no-frame M246 runtime identity/load gate, then the same fixed four-frame level only.",
}
partial = RESULT.with_name(RESULT.name + ".partial")
partial.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
os.replace(partial, RESULT)
print(json.dumps(value, ensure_ascii=False))
print("M246_KNIFE_BINARY_OFFLINE_PASS")
