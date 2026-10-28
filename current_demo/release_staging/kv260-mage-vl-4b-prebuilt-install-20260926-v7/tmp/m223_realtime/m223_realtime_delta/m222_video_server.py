#!/usr/bin/env python3
"""M222 service: M218 dual-source UI plus corrected worker and fast W4 decode."""

from __future__ import annotations

import video_server as _server

from m222_live_stream_core import M222ContinuousVideoEngine
from m222_vectorized_w4_runtime import M222PSVisionRuntime


class M222VideoRuntime(_server.M120VideoRuntime):
    def health(self) -> dict:
        value = super().health()
        value["backend"] = (
            "KV260 M222 vectorized PS W4 decode + accepted M207 FP32 Linear "
            "+ M120/M89X2 FPGA T32 language/head"
        )
        value["vision_decoder"] = "M222-vectorized-fourport-w4-v1"
        return value

    def stream(self, request):
        for name, payload in super().stream(request):
            payload = dict(payload)
            if name == "stage" and payload.get("name") == "vision":
                payload["label"] = "M222 向量化 W4 解码 + M207 FP32 视觉塔"
            if name == "complete" and isinstance(payload.get("proof"), dict):
                payload["proof"] = dict(payload["proof"])
                payload["proof"]["vision_backend"] = (
                    "M222 vectorized four-port W4 decode; accepted M207/M198 "
                    "FP32/BF16 precision boundaries"
                )
                if self.vision is not None:
                    payload["proof"]["vision_decoder_evidence"] = (
                        self.vision.decoder_evidence()
                    )
            yield name, payload


# The accepted M218 main/handler resolve these globals at runtime.
_server.ContinuousVideoEngine = M222ContinuousVideoEngine
_server.M207PSVisionRuntime = M222PSVisionRuntime
_server.M120VideoRuntime = M222VideoRuntime


if __name__ == "__main__":
    raise SystemExit(_server.main())

