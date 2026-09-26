#!/usr/bin/env python3
"""Install M261's bounded exact cache into the isolated M259 review path."""

from __future__ import annotations

import m222_video_server as _m222
import m259_video_runtime as _m259
import video_server as _server
from m261_budgeted_w4_runtime import M261BudgetedVariableFramePSVisionRuntime


_m222.M222PSVisionRuntime = M261BudgetedVariableFramePSVisionRuntime


class M261PreVisionKeyframeRuntime(_m259.M259PreVisionKeyframeRuntime):
    def health(self) -> dict:
        value = super().health()
        value.update({
            "m261_exact_bounded_w4_cache": True,
            "m261_cache_budget_mib": 64,
            "m261_cache_expected_used_mib": 63.609375,
            "m261_board_memory_gate": "pending",
        })
        return value


_server.M120VideoRuntime = M261PreVisionKeyframeRuntime
