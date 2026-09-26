#!/usr/bin/env python3
"""Bounded short-window action adapter for the M248 fast safety path.

The adapter is deliberately conservative.  It turns track-level temporal
features into auditable action labels, but it does not claim calibrated action
accuracy until target-scene labelled videos have been evaluated.
"""

from __future__ import annotations

from collections import defaultdict, deque
from dataclasses import dataclass
from math import hypot
from typing import Literal


ActionLabel = Literal[
    "WORKING",
    "IDLE",
    "WALKING",
    "FALLING",
    "FIGHTING",
    "UNKNOWN",
]


@dataclass(frozen=True)
class TrackFrameFeatures:
    track_id: int
    timestamp_ms: int
    bbox_xyxy: tuple[float, float, float, float]
    person_score: float
    motion_energy: float
    hand_motion: float
    task_interaction: float
    contact_score: float

    def validate(self) -> None:
        if self.track_id < 0 or self.timestamp_ms < 0:
            raise ValueError("track id and timestamp must be non-negative")
        x1, y1, x2, y2 = self.bbox_xyxy
        if any(value < 0.0 or value > 1.0 for value in self.bbox_xyxy):
            raise ValueError("bbox must be normalized")
        if x2 <= x1 or y2 <= y1:
            raise ValueError("bbox must have positive area")
        for name, value in (
            ("person_score", self.person_score),
            ("motion_energy", self.motion_energy),
            ("hand_motion", self.hand_motion),
            ("task_interaction", self.task_interaction),
            ("contact_score", self.contact_score),
        ):
            if value < 0.0 or value > 1.0:
                raise ValueError(f"{name} must be in [0,1]")


@dataclass(frozen=True)
class TemporalActionPolicy:
    history_size: int = 8
    minimum_frames: int = 4
    minimum_person_score: float = 0.50
    idle_displacement: float = 0.015
    walking_displacement: float = 0.045
    falling_vertical_displacement: float = 0.10
    falling_aspect_ratio: float = 1.05
    fighting_motion_energy: float = 0.60
    fighting_contact_score: float = 0.65
    working_task_interaction: float = 0.65
    working_hand_motion: float = 0.20
    thresholds_calibrated: bool = False

    def validate(self) -> None:
        if self.history_size < self.minimum_frames or self.minimum_frames < 2:
            raise ValueError("history_size must cover minimum_frames >= 2")
        values = (
            self.minimum_person_score,
            self.idle_displacement,
            self.walking_displacement,
            self.falling_vertical_displacement,
            self.fighting_motion_energy,
            self.fighting_contact_score,
            self.working_task_interaction,
            self.working_hand_motion,
        )
        if any(value < 0.0 or value > 1.0 for value in values):
            raise ValueError("policy thresholds must be in [0,1]")


def _center(box: tuple[float, float, float, float]) -> tuple[float, float]:
    x1, y1, x2, y2 = box
    return (0.5 * (x1 + x2), 0.5 * (y1 + y2))


def _aspect(box: tuple[float, float, float, float]) -> float:
    x1, y1, x2, y2 = box
    return (x2 - x1) / (y2 - y1)


def _mean(values: list[float]) -> float:
    return sum(values) / len(values)


class TemporalActionAdapter:
    """Maintain a bounded history per track and produce conservative labels."""

    def __init__(self, policy: TemporalActionPolicy | None = None):
        self.policy = policy or TemporalActionPolicy()
        self.policy.validate()
        self._history: dict[int, deque[TrackFrameFeatures]] = defaultdict(
            lambda: deque(maxlen=self.policy.history_size)
        )

    def update(self, feature: TrackFrameFeatures) -> dict:
        feature.validate()
        history = self._history[feature.track_id]
        if history and feature.timestamp_ms <= history[-1].timestamp_ms:
            raise ValueError("stale or duplicate track timestamp")
        history.append(feature)
        return self.classify(feature.track_id)

    def classify(self, track_id: int) -> dict:
        history = list(self._history.get(track_id, ()))
        if len(history) < self.policy.minimum_frames:
            return self._result(track_id, "UNKNOWN", 0.0, history, "insufficient-history")
        recent = history[-self.policy.minimum_frames :]
        if min(item.person_score for item in recent) < self.policy.minimum_person_score:
            return self._result(track_id, "UNKNOWN", 0.0, recent, "low-person-score")

        first_center = _center(recent[0].bbox_xyxy)
        last_center = _center(recent[-1].bbox_xyxy)
        displacement = hypot(last_center[0] - first_center[0], last_center[1] - first_center[1])
        horizontal_displacement = abs(last_center[0] - first_center[0])
        vertical_displacement = last_center[1] - first_center[1]
        final_aspect = _aspect(recent[-1].bbox_xyxy)
        motion = _mean([item.motion_energy for item in recent])
        hand_motion = _mean([item.hand_motion for item in recent])
        task_interaction = _mean([item.task_interaction for item in recent])
        contact = _mean([item.contact_score for item in recent])

        metrics = {
            "centroid_displacement": displacement,
            "horizontal_displacement": horizontal_displacement,
            "vertical_displacement": vertical_displacement,
            "final_aspect_ratio": final_aspect,
            "mean_motion_energy": motion,
            "mean_hand_motion": hand_motion,
            "mean_task_interaction": task_interaction,
            "mean_contact_score": contact,
        }

        if (
            vertical_displacement >= self.policy.falling_vertical_displacement
            and final_aspect >= self.policy.falling_aspect_ratio
        ):
            score = min(
                1.0,
                0.5 * vertical_displacement / self.policy.falling_vertical_displacement
                + 0.5 * final_aspect / self.policy.falling_aspect_ratio,
            )
            return self._result(track_id, "FALLING", score, recent, "rapid-down-and-horizontal", metrics)

        if (
            motion >= self.policy.fighting_motion_energy
            and contact >= self.policy.fighting_contact_score
        ):
            score = min(
                1.0,
                0.5 * motion / self.policy.fighting_motion_energy
                + 0.5 * contact / self.policy.fighting_contact_score,
            )
            return self._result(track_id, "FIGHTING", score, recent, "high-motion-and-contact", metrics)

        if (
            task_interaction >= self.policy.working_task_interaction
            and hand_motion >= self.policy.working_hand_motion
        ):
            score = min(
                1.0,
                0.5 * task_interaction / self.policy.working_task_interaction
                + 0.5 * hand_motion / self.policy.working_hand_motion,
            )
            return self._result(track_id, "WORKING", score, recent, "task-interaction-and-hand-motion", metrics)

        if horizontal_displacement >= self.policy.walking_displacement:
            score = min(1.0, horizontal_displacement / self.policy.walking_displacement)
            return self._result(track_id, "WALKING", score, recent, "horizontal-track-motion", metrics)

        if displacement <= self.policy.idle_displacement and motion <= self.policy.working_hand_motion:
            score = min(1.0, 1.0 - displacement / max(self.policy.idle_displacement, 1e-9))
            return self._result(track_id, "IDLE", score, recent, "low-motion-dwell", metrics)

        return self._result(track_id, "UNKNOWN", 0.0, recent, "ambiguous-features", metrics)

    def history_length(self, track_id: int) -> int:
        return len(self._history.get(track_id, ()))

    def _result(
        self,
        track_id: int,
        action: ActionLabel,
        score: float,
        history: list[TrackFrameFeatures],
        reason: str,
        metrics: dict | None = None,
    ) -> dict:
        return {
            "track_id": track_id,
            "action": action,
            "action_score": float(max(0.0, min(1.0, score))),
            "reason": reason,
            "history_frames": len(history),
            "window_start_ms": history[0].timestamp_ms if history else None,
            "window_end_ms": history[-1].timestamp_ms if history else None,
            "metrics": metrics or {},
            "thresholds_calibrated": self.policy.thresholds_calibrated,
        }
