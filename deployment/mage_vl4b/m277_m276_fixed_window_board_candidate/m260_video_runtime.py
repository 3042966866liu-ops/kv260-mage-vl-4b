#!/usr/bin/env python3
"""Install M260's exact W4 code cache into the isolated M259 review path."""

from __future__ import annotations

import m222_video_server as _m222
import m259_video_runtime as _m259
import video_server as _server
from m260_cached_w4_runtime import M260CachedVariableFramePSVisionRuntime


_m222.M222PSVisionRuntime = M260CachedVariableFramePSVisionRuntime


class M260PreVisionKeyframeRuntime(_m259.M259PreVisionKeyframeRuntime):
    def health(self) -> dict:
        value = super().health()
        value.update({
            "m260_exact_w4_component_cache": True,
            "m260_cache_precision": "uint8 codes + FP32 scales + int8 qmin",
            "m260_board_memory_gate": "pending",
        })
        return value


_server.M120VideoRuntime = M260PreVisionKeyframeRuntime
