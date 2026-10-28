#!/usr/bin/env python3
"""M258 visual state-boundary candidate built on the accepted M222 decoder.

Only the number of leading BF16 encoder blocks changes.  Packed W4 weights,
FP16 scales, FP32 Linear GEMM, attention/MLP implementation, and the final
output contract remain inherited from M222/M207.
"""

from __future__ import annotations

import time

import ps_vision_runtime as _base
from m206_ps_vision_runtime import M206ProgressLayer, _rss_mib
from m222_vectorized_w4_runtime import M222PSVisionRuntime


class M258PSVisionRuntime(M222PSVisionRuntime):
    """Select a fixed BF16 prefix and keep all later blocks in FP32."""

    def __init__(self, *args, bf16_prefix: int, **kwargs):
        prefix = int(bf16_prefix)
        if not 0 <= prefix <= 6:
            raise ValueError("M258 bf16_prefix must be in [0, 6]")
        self.bf16_prefix = prefix
        # M207's constructor deliberately reads the instance's class policy.
        # A per-instance tuple avoids modifying the accepted base class.
        self.FP32_LAYERS = tuple(range(prefix, 24))
        super().__init__(*args, **kwargs)
        heartbeat_seconds = float(kwargs.get("heartbeat_seconds", 30.0))
        progress_callback = kwargs.get("progress_callback")
        # M207 already installed progress-only wrappers.  Replace only those
        # wrappers so the emitted dtype label reflects the selected M258 math.
        for index, wrapped in enumerate(self.vision.encoder.layers):
            layer = wrapped.layer if isinstance(wrapped, M206ProgressLayer) else wrapped
            self.vision.encoder.layers[index] = M206ProgressLayer(
                layer,
                index=index,
                heartbeat_seconds=heartbeat_seconds,
                run_elapsed=self._elapsed,
                dtype_label=(
                    "BF16_BLOCK_FP32_LINEAR"
                    if index < self.bf16_prefix
                    else "FP32_BLOCK_FP32_LINEAR"
                ),
                progress_callback=progress_callback,
            )

    def __call__(self, pixel_values, image_grid_thw, patch_positions):
        self._vision_started = time.monotonic()
        print(
            "VISION_BEGIN layers=24 gemm_dtype=FP32 "
            f"bf16_prefix={self.bf16_prefix} "
            "w4_storage=M222-unchanged",
            flush=True,
        )
        passed = False
        try:
            # Skip M207's historical fixed-policy status text while executing
            # the same M90 model call with this instance's configured modules.
            output = _base.M90PSVisionRuntime.__call__(
                self, pixel_values, image_grid_thw, patch_positions
            )
            passed = True
            return output
        finally:
            print(
                f"VISION_{'PASS' if passed else 'FAIL'} "
                f"total_ms={self._elapsed() * 1000.0:.3f} "
                f"rss_mib={_rss_mib():.1f}",
                flush=True,
            )

    def state_policy_evidence(self) -> dict:
        return {
            "candidate": "M258-vision-state-boundary-sweep",
            "bf16_prefix_layers": list(range(self.bf16_prefix)),
            "fp32_layers": list(self.FP32_LAYERS),
            "packed_weight_layout": "M222 unchanged",
            "linear_gemm_dtype": "FP32 unchanged",
        }


class M258SelectedPSVisionRuntime(M258PSVisionRuntime):
    """Guard-banded selected policy: layers 0-1 BF16, layers 2-23 FP32."""

    def __init__(self, *args, **kwargs):
        if "bf16_prefix" in kwargs:
            raise TypeError("M258 selected policy does not accept a runtime override")
        super().__init__(*args, bf16_prefix=2, **kwargs)
