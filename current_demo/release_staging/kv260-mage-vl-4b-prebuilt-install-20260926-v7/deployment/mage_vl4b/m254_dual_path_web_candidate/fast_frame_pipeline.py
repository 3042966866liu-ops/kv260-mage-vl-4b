#!/usr/bin/env python3
"""Board-friendly frame-to-safety pipeline for M249/M250/M248.

This module consumes detector boxes, performs bounded IoU tracking, extracts
simple motion features from RGB frames with NumPy, invokes the M250 temporal
adapter, and emits the existing M248 safety-result contract.
"""

from __future__ import annotations

from collections import deque
from dataclasses import dataclass
import hashlib
from math import hypot

import numpy as np

from fast_safety_monitor import (
    BoundingBox,
    PersonActionObservation,
    SafetyWindowObservation,
)
from immediate_safety_monitor import ImmediateSafetyMonitor
from temporal_action_adapter import TemporalActionAdapter, TrackFrameFeatures


@dataclass(frozen=True)
class Detection:
    label: str
    score: float
    bbox_xyxy: tuple[float, float, float, float]

    def validate(self) -> None:
        if self.label not in {"person", "knife"}:
            raise ValueError(f"unsupported detection label: {self.label}")
        if not 0.0 <= self.score <= 1.0:
            raise ValueError("detection score must be in [0,1]")
        x1, y1, x2, y2 = self.bbox_xyxy
        if any(value < 0.0 or value > 1.0 for value in self.bbox_xyxy):
            raise ValueError("detection bbox must be normalized")
        if x2 <= x1 or y2 <= y1:
            raise ValueError("detection bbox must have positive area")


@dataclass(frozen=True)
class FastFramePolicy:
    person_threshold: float = 0.50
    knife_alarm_threshold: float = 0.80
    knife_safe_threshold: float = 0.20
    tracker_iou_threshold: float = 0.20
    tracker_center_distance: float = 0.15
    tracker_max_missed_frames: int = 2
    crop_size: int = 32
    task_zone_xyxy: tuple[float, float, float, float] | None = None
    thresholds_calibrated: bool = False

    def validate(self) -> None:
        numeric = (
            self.person_threshold,
            self.knife_alarm_threshold,
            self.knife_safe_threshold,
            self.tracker_iou_threshold,
            self.tracker_center_distance,
        )
        if any(value < 0.0 or value > 1.0 for value in numeric):
            raise ValueError("policy thresholds must be in [0,1]")
        if self.knife_safe_threshold >= self.knife_alarm_threshold:
            raise ValueError("knife safe threshold must be below alarm threshold")
        if self.tracker_max_missed_frames < 0 or self.crop_size < 8:
            raise ValueError("invalid tracker/crop bounds")
        if self.task_zone_xyxy is not None:
            Detection("person", 1.0, self.task_zone_xyxy).validate()


@dataclass
class _Track:
    track_id: int
    bbox_xyxy: tuple[float, float, float, float]
    missed: int = 0
    previous_crop: np.ndarray | None = None
    previous_upper_crop: np.ndarray | None = None


def _iou(a: tuple[float, float, float, float], b: tuple[float, float, float, float]) -> float:
    ax1, ay1, ax2, ay2 = a
    bx1, by1, bx2, by2 = b
    ix1, iy1, ix2, iy2 = max(ax1, bx1), max(ay1, by1), min(ax2, bx2), min(ay2, by2)
    intersection = max(0.0, ix2 - ix1) * max(0.0, iy2 - iy1)
    union = (ax2 - ax1) * (ay2 - ay1) + (bx2 - bx1) * (by2 - by1) - intersection
    return intersection / union if union > 0.0 else 0.0


def _center(box: tuple[float, float, float, float]) -> tuple[float, float]:
    x1, y1, x2, y2 = box
    return (0.5 * (x1 + x2), 0.5 * (y1 + y2))


def _gray_crop(frame: np.ndarray, box: tuple[float, float, float, float], size: int, upper: bool) -> np.ndarray:
    height, width, _ = frame.shape
    x1, y1, x2, y2 = box
    if upper:
        y2 = y1 + 0.55 * (y2 - y1)
    left = max(0, min(width - 1, int(round(x1 * (width - 1)))))
    right = max(left + 1, min(width, int(round(x2 * width))))
    top = max(0, min(height - 1, int(round(y1 * (height - 1)))))
    bottom = max(top + 1, min(height, int(round(y2 * height))))
    crop = frame[top:bottom, left:right]
    gray = (
        crop[..., 0].astype(np.float32) * 0.299
        + crop[..., 1].astype(np.float32) * 0.587
        + crop[..., 2].astype(np.float32) * 0.114
    )
    rows = np.linspace(0, gray.shape[0] - 1, size, dtype=np.int64)
    cols = np.linspace(0, gray.shape[1] - 1, size, dtype=np.int64)
    return np.ascontiguousarray(gray[np.ix_(rows, cols)])


def _motion(current: np.ndarray, previous: np.ndarray | None) -> float:
    if previous is None:
        return 0.0
    mean_absolute_difference = float(np.mean(np.abs(current - previous)))
    return min(1.0, mean_absolute_difference / 64.0)


class FastFramePipeline:
    def __init__(self, policy: FastFramePolicy | None = None):
        self.policy = policy or FastFramePolicy()
        self.policy.validate()
        self.monitor = ImmediateSafetyMonitor()
        self.actions = TemporalActionAdapter()
        self.tracks: dict[int, _Track] = {}
        self.next_track_id = 0
        self.sequence_history: deque[int] = deque(maxlen=4)
        self.last_sequence = -1

    def process_frame(
        self,
        *,
        frame_rgb: np.ndarray,
        detections: list[Detection],
        sequence: int,
        captured_unix_ms: int,
        evaluated_unix_ms: int,
    ) -> dict:
        if frame_rgb.ndim != 3 or frame_rgb.shape[2] != 3 or frame_rgb.dtype != np.uint8:
            raise ValueError("frame must be uint8 HWC RGB")
        if sequence <= self.last_sequence:
            raise ValueError("stale or duplicate frame sequence")
        if evaluated_unix_ms < captured_unix_ms:
            raise ValueError("evaluation cannot precede capture")
        for detection in detections:
            detection.validate()
        self.last_sequence = sequence
        self.sequence_history.append(sequence)

        people = [item for item in detections if item.label == "person" and item.score >= self.policy.person_threshold]
        assignments = self._assign_tracks(people)
        contact_scores = self._contact_scores(assignments)
        observations = []
        for detection, track in assignments:
            crop = _gray_crop(frame_rgb, detection.bbox_xyxy, self.policy.crop_size, upper=False)
            upper_crop = _gray_crop(frame_rgb, detection.bbox_xyxy, self.policy.crop_size, upper=True)
            motion = _motion(crop, track.previous_crop)
            hand_motion = _motion(upper_crop, track.previous_upper_crop)
            track.previous_crop = crop
            track.previous_upper_crop = upper_crop
            task_interaction = self._task_interaction(detection.bbox_xyxy)
            action = self.actions.update(TrackFrameFeatures(
                track_id=track.track_id,
                timestamp_ms=captured_unix_ms,
                bbox_xyxy=detection.bbox_xyxy,
                person_score=detection.score,
                motion_energy=motion,
                hand_motion=hand_motion,
                task_interaction=task_interaction,
                contact_score=contact_scores[track.track_id],
            ))
            observations.append(PersonActionObservation(
                track_id=track.track_id,
                bbox=BoundingBox(*detection.bbox_xyxy),
                action=action["action"],
                action_score=action["action_score"],
                person_score=detection.score,
            ))

        knife_scores = [item.score for item in detections if item.label == "knife"]
        knife_score = max(knife_scores) if knife_scores else 0.0
        if knife_score >= self.policy.knife_alarm_threshold:
            knife_verdict = "PRESENT"
        elif knife_score <= self.policy.knife_safe_threshold:
            knife_verdict = "ABSENT"
        else:
            knife_verdict = "UNCERTAIN"
        evidence = hashlib.sha256(
            str(tuple(frame_rgb.shape)).encode("ascii") + frame_rgb.tobytes(order="C")
        ).hexdigest()
        event = self.monitor.update(SafetyWindowObservation(
            window_index=sequence,
            sequences=tuple(self.sequence_history),
            evidence_sha256=evidence,
            captured_unix_ms=captured_unix_ms,
            evaluated_unix_ms=evaluated_unix_ms,
            people=tuple(observations),
            knife_verdict=knife_verdict,
            knife_score=knife_score,
            raw_knife_output=f"detector_score={knife_score:.6f}",
        ))
        event["fast_pipeline"] = {
            "detector": "M249-SSDLite",
            "tracker": "bounded-greedy-IoU-v1",
            "action_adapter": "M250-temporal-rules-v1",
            "task_zone_configured": self.policy.task_zone_xyxy is not None,
            "thresholds_calibrated": self.policy.thresholds_calibrated,
            "active_track_count": len(self.tracks),
        }
        return event

    def _assign_tracks(self, people: list[Detection]) -> list[tuple[Detection, _Track]]:
        unmatched = set(self.tracks)
        assignments: list[tuple[Detection, _Track]] = []
        for detection in people:
            best_id = None
            best_value = -1.0
            dc = _center(detection.bbox_xyxy)
            for track_id in unmatched:
                track = self.tracks[track_id]
                overlap = _iou(detection.bbox_xyxy, track.bbox_xyxy)
                tc = _center(track.bbox_xyxy)
                distance = hypot(dc[0] - tc[0], dc[1] - tc[1])
                eligible = overlap >= self.policy.tracker_iou_threshold or distance <= self.policy.tracker_center_distance
                value = overlap - 0.1 * distance
                if eligible and value > best_value:
                    best_id, best_value = track_id, value
            if best_id is None:
                best_id = self.next_track_id
                self.next_track_id += 1
                self.tracks[best_id] = _Track(best_id, detection.bbox_xyxy)
            track = self.tracks[best_id]
            track.bbox_xyxy = detection.bbox_xyxy
            track.missed = 0
            unmatched.discard(best_id)
            assignments.append((detection, track))
        for track_id in list(unmatched):
            self.tracks[track_id].missed += 1
            if self.tracks[track_id].missed > self.policy.tracker_max_missed_frames:
                del self.tracks[track_id]
        return assignments

    def _contact_scores(self, assignments: list[tuple[Detection, _Track]]) -> dict[int, float]:
        values = {track.track_id: 0.0 for _, track in assignments}
        for left in range(len(assignments)):
            _, left_track = assignments[left]
            left_center = _center(left_track.bbox_xyxy)
            for right in range(left + 1, len(assignments)):
                _, right_track = assignments[right]
                right_center = _center(right_track.bbox_xyxy)
                distance = hypot(left_center[0] - right_center[0], left_center[1] - right_center[1])
                proximity = max(0.0, 1.0 - distance / 0.30)
                overlap = _iou(left_track.bbox_xyxy, right_track.bbox_xyxy)
                score = max(proximity, min(1.0, overlap * 2.0))
                values[left_track.track_id] = max(values[left_track.track_id], score)
                values[right_track.track_id] = max(values[right_track.track_id], score)
        return values

    def _task_interaction(self, person_box: tuple[float, float, float, float]) -> float:
        zone = self.policy.task_zone_xyxy
        if zone is None:
            return 0.0
        center = _center(person_box)
        zx1, zy1, zx2, zy2 = zone
        return 1.0 if zx1 <= center[0] <= zx2 and zy1 <= center[1] <= zy2 else 0.0
