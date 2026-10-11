#!/usr/bin/env python3
"""Offline contract gate for the M247 knife-alarm Web surface."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
STATIC = ROOT / "deployment/mage_vl4b/m247_knife_alarm_web_source/static"
M246_BINARY = ROOT / "deployment/mage_vl4b/m246_knife_binary_source/m246_knife_binary.py"
RESULT = ROOT / "deployment/mage_vl4b/M247_KNIFE_ALARM_WEB_OFFLINE_RESULT.json"


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> int:
    index = (STATIC / "index.html").read_text(encoding="utf-8")
    app = (STATIC / "app.js").read_text(encoding="utf-8")
    style = (STATIC / "style.css").read_text(encoding="utf-8")
    binary = M246_BINARY.read_text(encoding="utf-8")
    prompt = (
        "[TELLME_KNIFE_BINARY_V1] Inspect the four video frames. "
        "Output exactly one character: 1 if any knife is visible, otherwise 0. Answer:"
    )

    checks = {
        "three_static_members": sorted(path.name for path in STATIC.iterdir() if path.is_file())
        == ["app.js", "index.html", "style.css"],
        "fixed_prompt_matches_m246": prompt in index and all(part in binary for part in (
            "[TELLME_KNIFE_BINARY_V1] Inspect the four video frames. ",
            "Output exactly one character: 1 if any knife is visible, otherwise 0. Answer:",
        )),
        "prompt_not_user_editable": 'id="prompt" type="hidden"' in index,
        "one_token_locked": 'id="max-tokens" type="hidden" value="1"' in index,
        "observation_sse_consumed": "'knife_observation'" in app,
        "alarm_sse_consumed": "'knife_alarm'" in app,
        "all_alarm_states_rendered": all(token in app for token in ("ALARM", "SAFE", "REVIEW")),
        "alarm_is_assertive": 'aria-live="assertive"' in index,
        "evidence_sha_visible": 'id="evidence-sha"' in index and "evidence_sha256" in app,
        "build_kernel_visible": 'id="build-kernel"' in index and "proof.build_id" in app,
        "window_identity_visible": 'id="window-sequences"' in index and "observation.sequences" in app,
        "actual_window_latency_visible": 'id="alarm-latency"' in index and "currentWindowStartedAt" in app,
        "uncalibrated_score_label": "未校准二元分数" in index,
        "score_disclaimer_explicit": "不是检测准确率或置信度" in index,
        "no_confidence_metric_field": 'id="confidence"' not in index and "confidence:" not in app,
        "no_accuracy_metric_field": 'id="accuracy"' not in index and "accuracy:" not in app,
        "not_second_level_claim": "尚未达到秒级更新" in index and "目标 < 5 s" in app,
        "latest_only_visible": "continuous-latest-only" in index,
        "camera_and_file_sources_preserved": all(token in index for token in (
            'id="camera"', 'id="video-file"', 'id="stop"',
        )),
        "alarm_visual_states_styled": all(token in style for token in (
            ".alarm-card.alarm", ".alarm-card.safe", ".alarm-card.review",
        )),
    }
    failed = [name for name, passed in checks.items() if not passed]
    payload = {
        "gate": "M247-knife-alarm-web-offline-contract",
        "status": "PASS" if not failed else "FAIL",
        "checks": checks,
        "failed_checks": failed,
        "static_members": {
            path.name: {"bytes": path.stat().st_size, "sha256": sha256(path)}
            for path in sorted(STATIC.iterdir())
            if path.is_file()
        },
        "scope": (
            "Offline HTML/CSS/JS and M246 SSE contract only; not board, browser visual QA, "
            "knife accuracy, calibrated threshold, fixed-window, continuous-video, or real-time PASS."
        ),
    }
    RESULT.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0 if not failed else 1


if __name__ == "__main__":
    raise SystemExit(main())
