#!/usr/bin/env python3
"""Fail-closed continuous-stream worker for the M222 candidate."""

from __future__ import annotations

import asyncio
import threading
import time

from live_stream_core import ContinuousVideoEngine as _M218ContinuousVideoEngine


class M222ContinuousVideoEngine(_M218ContinuousVideoEngine):
    """Give PYNQ an event loop and make worker death visible to HTTP clients."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.worker_error: str | None = None
        self.worker_started_monotonic: float | None = None
        self.worker_stopped_monotonic: float | None = None

    def _worker(self) -> None:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        self.worker_started_monotonic = time.monotonic()
        self.events.publish("worker", {"status": "loading"})
        try:
            super()._worker()
        except BaseException as error:
            self.worker_error = f"{type(error).__name__}: {error}"
            self.events.publish("worker", {
                "status": "failed",
                "error": self.worker_error,
            })
        finally:
            self.worker_stopped_monotonic = time.monotonic()
            asyncio.set_event_loop(None)
            loop.close()

    def status(self) -> dict:
        value = super().status()
        thread = self._thread
        worker_alive = bool(thread is not None and thread.is_alive())
        runtime_loading = bool(
            worker_alive and self.runtime_load_count == 0 and self.worker_error is None
        )
        if self.worker_error is not None:
            service_state = "worker-failed"
        elif runtime_loading:
            service_state = "runtime-loading"
        elif worker_alive and self.runtime_load_count == 1:
            service_state = "ready"
        elif worker_alive:
            service_state = "starting"
        else:
            service_state = "stopped"
        value.update({
            "service_state": service_state,
            "worker_alive": worker_alive,
            "runtime_loading": runtime_loading,
            "worker_error": self.worker_error,
            "worker_started_monotonic": self.worker_started_monotonic,
            "worker_stopped_monotonic": self.worker_stopped_monotonic,
        })
        return value

