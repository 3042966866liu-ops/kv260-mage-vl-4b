#!/usr/bin/env python3
"""Isolated M335 Web entry: M333 scheduler with M276 fixed 159-token review.

This module does not change the installed M254 service or its alarm threshold.
"""

from __future__ import annotations

from http import HTTPStatus
from pathlib import Path
from urllib.parse import urlparse

import m254_video_server as m254
import m276_video_runtime as m276
from m335_review_bridge import AlarmReviewScheduler, SemanticTerminalMonitor

# The M276 module installs the previously board-verified short review runtime.
# Pin it after importing M254 so its M243 import cannot restore the long path.
m254._server.M120VideoRuntime = m276.M276ShortPromptBinaryRuntime


class M335DualPathController(m254.M254DualPathController):
    def __init__(self, runtime):
        super().__init__(runtime)
        self._terminal_monitor: SemanticTerminalMonitor | None = None

    def _submit_review_with_identity(self, frames: tuple) -> tuple[int, ...]:
        if self.engine is None:
            raise RuntimeError("MODEL_NOT_READY: semantic engine is not active")
        return tuple(self.engine.frames.push(frame) for frame in frames)

    def start(self, prompt: str, max_new_tokens: int,
              source_mode: str = "browser-camera", source_label: str = "") -> dict:
        super().start(prompt, max_new_tokens, source_mode, source_label)
        if self.engine is None or self.fast_engine is None:
            raise RuntimeError("MODEL_NOT_READY: parent did not create both engines")
        bridge = AlarmReviewScheduler(self._publish, self._submit_review_with_identity)
        self.review = bridge
        self.fast_engine.pipeline.callback = bridge.on_fast_result
        monitor = SemanticTerminalMonitor(self.engine.events, bridge)
        monitor.start()
        self._terminal_monitor = monitor
        self._publish("semantic_review_policy", {
            "policy": "one-active-one-latest-waiting",
            "manual_review_available": True,
            "automatic_alarm_threshold_unchanged": True,
            "stable_build_id_expected": "0x4D395832",
            "candidate_not_promoted": True,
        })
        return self.status()

    def request_manual_review(self) -> dict:
        if self.engine is None or self.review is None:
            raise RuntimeError("MODEL_NOT_READY: live session has not started")
        if self._terminal_monitor is None or self._terminal_monitor.error:
            raise RuntimeError("MODEL_NOT_READY: semantic terminal monitor is unavailable")
        if self.runtime.board is None or self.engine.runtime_load_count != 1:
            raise RuntimeError("MODEL_NOT_READY: 4B/FPGA runtime has not reported ready")
        return self.review.request_manual_review()

    def status(self) -> dict:
        value = super().status()
        monitor = self._terminal_monitor
        value["semantic_terminal_monitor_error"] = None if monitor is None else monitor.error
        value["manual_review_available"] = (
            self.engine is not None and self.review is not None
            and monitor is not None and monitor.error is None
            and self.runtime.board is not None and self.engine.runtime_load_count == 1
        )
        value["candidate_module_path"] = str(Path(__file__).resolve())
        value["m254_module_path"] = str(Path(m254.__file__).resolve())
        value["semantic_runtime_class"] = m254._server.M120VideoRuntime.__name__
        value["semantic_input_contract"] = "M276 latest source frame, two views, 159 tokens, restricted 0/1"
        return value

    def close(self) -> None:
        monitor = self._terminal_monitor
        self._terminal_monitor = None
        if monitor is not None:
            monitor.close()
        super().close()


class M335Handler(m254._server.Handler):
    def do_POST(self) -> None:
        if urlparse(self.path).path != "/api/4b/video/live/review":
            return super().do_POST()
        length = self.headers.get("Content-Length", "0")
        if length != "0":
            self.send_json(HTTPStatus.BAD_REQUEST, {
                "accepted": False, "code": "INVALID_REQUEST", "error": "manual review takes no body",
            })
            return
        try:
            result = self.controller.request_manual_review()
            self.send_json(HTTPStatus.ACCEPTED, result)
        except ValueError as error:
            self.send_json(HTTPStatus.CONFLICT, {
                "accepted": False, "code": "MISSING_FRAMES", "error": str(error),
            })
        except RuntimeError as error:
            message = str(error)
            code = message.split(":", 1)[0]
            status = HTTPStatus.SERVICE_UNAVAILABLE if code == "MODEL_NOT_READY" else HTTPStatus.CONFLICT
            if code == "SUBMISSION_FAILED":
                status = HTTPStatus.INTERNAL_SERVER_ERROR
            self.send_json(status, {"accepted": False, "code": code, "error": message})


m254._server.LiveController = M335DualPathController
m254._server.Handler = M335Handler
m254._server.STATIC = Path(__file__).resolve().parent / "static"


if __name__ == "__main__":
    raise SystemExit(m254._server.main())
