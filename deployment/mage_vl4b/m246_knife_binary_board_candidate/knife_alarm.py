#!/usr/bin/env python3
"""Deterministic knife-alert contract for latest-only video windows.

This module does not claim that a model is accurate.  It converts an explicit
model/detector observation into an auditable alarm state while preserving the
window identity and evidence hash.  Thresholds remain UNCALIBRATED until a
labelled target-scene validation set is evaluated.
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from typing import Literal


Verdict = Literal["PRESENT", "ABSENT", "UNCERTAIN"]
AlarmState = Literal["ALARM", "SAFE", "REVIEW"]


@dataclass(frozen=True)
class KnifeAlarmPolicy:
    score_alarm_threshold: float = 0.80
    score_safe_threshold: float = 0.20
    positive_windows_to_alarm: int = 1
    absent_windows_to_clear: int = 2
    thresholds_calibrated: bool = False

    def validate(self) -> None:
        if not 0.0 <= self.score_safe_threshold < self.score_alarm_threshold <= 1.0:
            raise ValueError("knife score thresholds must satisfy 0 <= safe < alarm <= 1")
        if self.positive_windows_to_alarm < 1 or self.absent_windows_to_clear < 1:
            raise ValueError("window confirmation counts must be positive")


@dataclass(frozen=True)
class KnifeObservation:
    window_index: int
    sequences: tuple[int, ...]
    evidence_sha256: str
    verdict: Verdict
    score: float | None = None
    raw_model_output: str = ""
    captured_unix_ms: int | None = None

    def validate(self) -> None:
        if self.window_index < 0:
            raise ValueError("window_index must be non-negative")
        if len(self.sequences) != 4 or tuple(sorted(self.sequences)) != self.sequences:
            raise ValueError("knife observation requires four ordered frame sequences")
        if len(self.evidence_sha256) != 64:
            raise ValueError("evidence_sha256 must contain 64 hexadecimal characters")
        int(self.evidence_sha256, 16)
        if self.score is not None and not 0.0 <= self.score <= 1.0:
            raise ValueError("score must be within [0,1]")


def parse_binary_model_output(raw: str) -> Verdict:
    """Parse only an explicit one-symbol or JSON answer; never guess from prose."""
    text = raw.strip()
    if text == "1":
        return "PRESENT"
    if text == "0":
        return "ABSENT"
    if text == "?":
        return "UNCERTAIN"
    try:
        value = json.loads(text)
    except (json.JSONDecodeError, TypeError):
        return "UNCERTAIN"
    if isinstance(value, dict) and value.get("knife_present") is True:
        return "PRESENT"
    if isinstance(value, dict) and value.get("knife_present") is False:
        return "ABSENT"
    return "UNCERTAIN"


class KnifeAlarmStateMachine:
    """Immediate positive alarm, conservative clear, fail-visible uncertainty."""

    def __init__(self, policy: KnifeAlarmPolicy | None = None):
        self.policy = policy or KnifeAlarmPolicy()
        self.policy.validate()
        self.state: AlarmState = "REVIEW"
        self.last_window_index = -1
        self.consecutive_present = 0
        self.consecutive_absent = 0
        self.last_alarm_evidence: dict | None = None

    def _effective_verdict(self, observation: KnifeObservation) -> Verdict:
        if observation.score is None:
            return observation.verdict
        if observation.score >= self.policy.score_alarm_threshold:
            return "PRESENT"
        if observation.score <= self.policy.score_safe_threshold:
            return "ABSENT"
        return "UNCERTAIN"

    def update(self, observation: KnifeObservation) -> dict:
        observation.validate()
        if observation.window_index <= self.last_window_index:
            raise ValueError("stale or duplicate knife observation refused")
        self.last_window_index = observation.window_index
        effective = self._effective_verdict(observation)

        if effective == "PRESENT":
            self.consecutive_present += 1
            self.consecutive_absent = 0
            if self.consecutive_present >= self.policy.positive_windows_to_alarm:
                self.state = "ALARM"
                self.last_alarm_evidence = {
                    "window_index": observation.window_index,
                    "sequences": list(observation.sequences),
                    "evidence_sha256": observation.evidence_sha256,
                    "captured_unix_ms": observation.captured_unix_ms,
                }
        elif effective == "ABSENT":
            self.consecutive_absent += 1
            self.consecutive_present = 0
            if self.consecutive_absent >= self.policy.absent_windows_to_clear:
                self.state = "SAFE"
        else:
            self.consecutive_present = 0
            self.consecutive_absent = 0
            if self.state != "ALARM":
                self.state = "REVIEW"

        return {
            "event": "knife_alarm",
            "state": self.state,
            "effective_verdict": effective,
            "observation": asdict(observation),
            "consecutive_present": self.consecutive_present,
            "consecutive_absent": self.consecutive_absent,
            "policy": asdict(self.policy),
            "last_alarm_evidence": self.last_alarm_evidence,
            "calibration_required": not self.policy.thresholds_calibrated,
        }

