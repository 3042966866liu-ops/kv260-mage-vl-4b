#!/usr/bin/env python3
"""Experimental M254 Web entry point with reusable semantic-review scheduling.

Never replace the installed M254 service with this file without the separate
package, dependency, HTTP, board and rollback gates. The stable path remains
the default.
"""

from __future__ import annotations

import m254_video_server as m254
from m333_review_bridge import AlarmReviewScheduler, SemanticTerminalMonitor


class M333DualPathController(m254.M254DualPathController):
    def __init__(self, runtime):
        super().__init__(runtime)
        self._terminal_monitor: SemanticTerminalMonitor | None = None

    def _submit_review_with_identity(self, frames: tuple) -> tuple[int, ...]:
        engine = self.engine
        if engine is None:
            raise RuntimeError("M333 semantic engine is not active")
        return tuple(engine.frames.push(frame) for frame in frames)

    def start(self, prompt: str, max_new_tokens: int,
              source_mode: str = "browser-camera", source_label: str = "") -> dict:
        # Parent performs the unchanged predecessor, model and runtime checks.
        # No frame can be accepted before this start request returns, so the
        # original unexercised bridge can be replaced without losing input.
        super().start(prompt, max_new_tokens, source_mode, source_label)
        engine = self.engine
        fast = self.fast_engine
        if engine is None or fast is None:
            raise RuntimeError("M333 parent start did not create both engines")
        bridge = AlarmReviewScheduler(self._publish, self._submit_review_with_identity)
        self.review = bridge
        fast.pipeline.callback = bridge.on_fast_result
        monitor = SemanticTerminalMonitor(engine.events, bridge)
        monitor.start()
        self._terminal_monitor = monitor
        self._publish("semantic_review_policy", {
            "policy": "alarm-only-one-active-one-latest-waiting",
            "stable_build_id_expected": "0x4D395832",
            "candidate_not_promoted": True,
        })
        return self.status()

    def status(self) -> dict:
        value = super().status()
        monitor = self._terminal_monitor
        value["semantic_terminal_monitor_error"] = None if monitor is None else monitor.error
        return value

    def close(self) -> None:
        monitor = self._terminal_monitor
        self._terminal_monitor = None
        if monitor is not None:
            monitor.close()
        super().close()


m254._server.LiveController = M333DualPathController


if __name__ == "__main__":
    raise SystemExit(m254._server.main())
