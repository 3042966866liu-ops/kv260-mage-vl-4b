#!/usr/bin/env python3
"""Per-frame knife alarm plus bounded-window action event composition.

M245 intentionally required a complete four-frame language-model window.  The
fast detector path has a different safety requirement: a confident knife on
the first frame must alarm immediately.  This state machine keeps the same Web
event fields without inventing or padding frame sequence identities.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass

from fast_safety_monitor import SafetyWindowObservation


@dataclass(frozen=True)
class ImmediateSafetyPolicy:
    target_update_period_ms: int = 5000
    minimum_action_score: float = 0.50
    knife_alarm_threshold: float = 0.80
    knife_safe_threshold: float = 0.20
    absent_frames_to_clear: int = 2
    thresholds_calibrated: bool = False

    def validate(self) -> None:
        if self.target_update_period_ms <= 0 or self.absent_frames_to_clear < 1:
            raise ValueError("invalid deadline/clear count")
        if not 0.0 <= self.minimum_action_score <= 1.0:
            raise ValueError("invalid action threshold")
        if not 0.0 <= self.knife_safe_threshold < self.knife_alarm_threshold <= 1.0:
            raise ValueError("invalid knife thresholds")


class ImmediateSafetyMonitor:
    def __init__(self, policy: ImmediateSafetyPolicy | None = None):
        self.policy = policy or ImmediateSafetyPolicy()
        self.policy.validate()
        self.last_window_index = -1
        self.state = "REVIEW"
        self.consecutive_absent = 0
        self.last_alarm_evidence: dict | None = None

    def update(self, observation: SafetyWindowObservation) -> dict:
        observation.validate()
        if observation.window_index <= self.last_window_index:
            raise ValueError("stale or duplicate safety window refused")
        self.last_window_index = observation.window_index

        score = observation.knife_score
        if score is None:
            effective = observation.knife_verdict
        elif score >= self.policy.knife_alarm_threshold:
            effective = "PRESENT"
        elif score <= self.policy.knife_safe_threshold:
            effective = "ABSENT"
        else:
            effective = "UNCERTAIN"

        if effective == "PRESENT":
            self.state = "ALARM"
            self.consecutive_absent = 0
            self.last_alarm_evidence = {
                "window_index": observation.window_index,
                "sequences": list(observation.sequences),
                "evidence_sha256": observation.evidence_sha256,
                "captured_unix_ms": observation.captured_unix_ms,
            }
        elif effective == "ABSENT":
            self.consecutive_absent += 1
            if self.consecutive_absent >= self.policy.absent_frames_to_clear:
                self.state = "SAFE"
        else:
            self.consecutive_absent = 0
            if self.state != "ALARM":
                self.state = "REVIEW"

        people = []
        action_counts: dict[str, int] = {}
        for person in observation.people:
            action = person.action if person.action_score >= self.policy.minimum_action_score else "UNKNOWN"
            action_counts[action] = action_counts.get(action, 0) + 1
            people.append({
                "track_id": person.track_id,
                "bbox_xyxy_normalized": asdict(person.bbox),
                "person_score": person.person_score,
                "action": action,
                "action_score": person.action_score,
                "action_threshold_calibrated": self.policy.thresholds_calibrated,
            })

        latency_ms = observation.evaluated_unix_ms - observation.captured_unix_ms
        alarm = self.state == "ALARM"
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
                "verdict": effective,
                "score": score,
                "thresholds_calibrated": self.policy.thresholds_calibrated,
            },
            "alarm": {
                "active": alarm,
                "state": self.state,
                "code": "KNIFE_DETECTED" if alarm else None,
                "icon": "⚠" if alarm else "",
                "badge_text": "刀具报警" if alarm else "",
                "badge_style": "danger" if alarm else "safe",
                "evidence_frame_sha256": (
                    self.last_alarm_evidence["evidence_sha256"]
                    if alarm and self.last_alarm_evidence is not None
                    else None
                ),
            },
            "slow_vlm_review": {
                "required": alarm or self.state == "REVIEW",
                "blocks_fast_alarm": False,
            },
            "policy": asdict(self.policy),
        }
