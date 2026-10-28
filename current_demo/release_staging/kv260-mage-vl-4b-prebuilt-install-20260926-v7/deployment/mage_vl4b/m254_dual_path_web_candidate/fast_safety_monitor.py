#!/usr/bin/env python3
"""Model-independent fast safety-monitor contract.

The slow Mage-VL 4B path is not used to produce an immediate alarm.  A fast
detector/action adapter supplies structured observations to this state machine;
Mage-VL may review an event asynchronously without delaying the alarm.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Literal

from knife_alarm import (
    KnifeAlarmPolicy,
    KnifeAlarmStateMachine,
    KnifeObservation,
    Verdict,
)


ActionLabel = Literal[
    "WORKING",
    "IDLE",
    "WALKING",
    "FALLING",
    "FIGHTING",
    "UNKNOWN",
]


@dataclass(frozen=True)
class BoundingBox:
    """Normalized xyxy box in the source frame."""

    x1: float
    y1: float
    x2: float
    y2: float

    def validate(self) -> None:
        values = (self.x1, self.y1, self.x2, self.y2)
        if any(value < 0.0 or value > 1.0 for value in values):
            raise ValueError("bounding box coordinates must be normalized to [0,1]")
        if self.x2 <= self.x1 or self.y2 <= self.y1:
            raise ValueError("bounding box must have positive width and height")


@dataclass(frozen=True)
class PersonActionObservation:
    track_id: int
    bbox: BoundingBox
    action: ActionLabel
    action_score: float
    person_score: float

    def validate(self) -> None:
        if self.track_id < 0:
            raise ValueError("track_id must be non-negative")
        self.bbox.validate()
        if self.action not in {
            "WORKING", "IDLE", "WALKING", "FALLING", "FIGHTING", "UNKNOWN"
        }:
            raise ValueError(f"unsupported action label: {self.action}")
        if not 0.0 <= self.action_score <= 1.0:
            raise ValueError("action_score must be within [0,1]")
        if not 0.0 <= self.person_score <= 1.0:
            raise ValueError("person_score must be within [0,1]")


@dataclass(frozen=True)
class SafetyWindowObservation:
    window_index: int
    sequences: tuple[int, ...]
    evidence_sha256: str
    captured_unix_ms: int
    evaluated_unix_ms: int
    people: tuple[PersonActionObservation, ...]
    knife_verdict: Verdict
    knife_score: float | None
    raw_knife_output: str = ""

    def validate(self) -> None:
        if self.window_index < 0:
            raise ValueError("window_index must be non-negative")
        if len(self.sequences) < 1 or tuple(sorted(self.sequences)) != self.sequences:
            raise ValueError("frame sequences must be non-empty and ordered")
        if len(set(self.sequences)) != len(self.sequences):
            raise ValueError("frame sequences must not contain duplicates")
        if len(self.evidence_sha256) != 64:
            raise ValueError("evidence_sha256 must contain 64 hexadecimal characters")
        int(self.evidence_sha256, 16)
        if self.evaluated_unix_ms < self.captured_unix_ms:
            raise ValueError("evaluated time must not precede capture time")
        if self.knife_score is not None and not 0.0 <= self.knife_score <= 1.0:
            raise ValueError("knife_score must be within [0,1]")
        track_ids: set[int] = set()
        for person in self.people:
            person.validate()
            if person.track_id in track_ids:
                raise ValueError("duplicate track_id in one window")
            track_ids.add(person.track_id)


@dataclass(frozen=True)
class FastSafetyPolicy:
    target_update_period_ms: int = 5000
    minimum_action_score: float = 0.50
    knife_alarm_threshold: float = 0.80
    knife_safe_threshold: float = 0.20
    absent_windows_to_clear: int = 2
    thresholds_calibrated: bool = False

    def validate(self) -> None:
        if self.target_update_period_ms <= 0:
            raise ValueError("target_update_period_ms must be positive")
        if not 0.0 <= self.minimum_action_score <= 1.0:
            raise ValueError("minimum_action_score must be within [0,1]")
        KnifeAlarmPolicy(
            score_alarm_threshold=self.knife_alarm_threshold,
            score_safe_threshold=self.knife_safe_threshold,
            positive_windows_to_alarm=1,
            absent_windows_to_clear=self.absent_windows_to_clear,
            thresholds_calibrated=self.thresholds_calibrated,
        ).validate()


class FastSafetyMonitor:
    """Convert fast-path observations into an auditable Web/SSE result."""

    def __init__(self, policy: FastSafetyPolicy | None = None):
        self.policy = policy or FastSafetyPolicy()
        self.policy.validate()
        self.knife = KnifeAlarmStateMachine(
            KnifeAlarmPolicy(
                score_alarm_threshold=self.policy.knife_alarm_threshold,
                score_safe_threshold=self.policy.knife_safe_threshold,
                positive_windows_to_alarm=1,
                absent_windows_to_clear=self.policy.absent_windows_to_clear,
                thresholds_calibrated=self.policy.thresholds_calibrated,
            )
        )
        self.last_window_index = -1

    def update(self, observation: SafetyWindowObservation) -> dict:
        observation.validate()
        if observation.window_index <= self.last_window_index:
            raise ValueError("stale or duplicate safety window refused")
        self.last_window_index = observation.window_index

        knife_event = self.knife.update(
            KnifeObservation(
                window_index=observation.window_index,
                sequences=tuple(observation.sequences[-4:]),
                evidence_sha256=observation.evidence_sha256,
                verdict=observation.knife_verdict,
                score=observation.knife_score,
                raw_model_output=observation.raw_knife_output,
                captured_unix_ms=observation.captured_unix_ms,
            )
        )

        people = []
        action_counts: dict[str, int] = {}
        for person in observation.people:
            action = (
                person.action
                if person.action_score >= self.policy.minimum_action_score
                else "UNKNOWN"
            )
            action_counts[action] = action_counts.get(action, 0) + 1
            people.append(
                {
                    "track_id": person.track_id,
                    "bbox_xyxy_normalized": asdict(person.bbox),
                    "person_score": person.person_score,
                    "action": action,
                    "action_score": person.action_score,
                    "action_threshold_calibrated": self.policy.thresholds_calibrated,
                }
            )

        latency_ms = observation.evaluated_unix_ms - observation.captured_unix_ms
        alarm = knife_event["state"] == "ALARM"
        return {
            "event": "safety_result",
            "window_index": observation.window_index,
            "window_sequences": list(observation.sequences),
            "evidence_sha256": observation.evidence_sha256,
            "capture_to_result_ms": latency_ms,
            "target_update_period_ms": self.policy.target_update_period_ms,
            "realtime_deadline_met": latency_ms <= self.policy.target_update_period_ms,
            "people": people,
            "person_count": len(people),
            "action_counts": action_counts,
            "knife": {
                "verdict": knife_event["effective_verdict"],
                "score": observation.knife_score,
                "thresholds_calibrated": self.policy.thresholds_calibrated,
            },
            "alarm": {
                "active": alarm,
                "state": knife_event["state"],
                "code": "KNIFE_DETECTED" if alarm else None,
                "icon": "⚠" if alarm else "",
                "badge_text": "刀具报警" if alarm else "",
                "badge_style": "danger" if alarm else "safe",
                "evidence_frame_sha256": observation.evidence_sha256 if alarm else None,
            },
            "slow_vlm_review": {
                "required": alarm or knife_event["state"] == "REVIEW",
                "blocks_fast_alarm": False,
            },
            "policy": asdict(self.policy),
        }
