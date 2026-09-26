#!/usr/bin/env python3
"""M269 four-view 224 visual runtime over the exact M261 cache policy."""

from __future__ import annotations

import time

import numpy as np

from m206_ps_vision_runtime import _rss_mib
from m261_budgeted_w4_runtime import M261BudgetedVariableFramePSVisionRuntime


class M269MultiscalePSVisionRuntime(M261BudgetedVariableFramePSVisionRuntime):
    """Execute unchanged visual math with four 14x14 patch-grid views."""

    def __call__(self, pixel_values, image_grid_thw, patch_positions):
        pixels_np = np.asarray(pixel_values, dtype=np.float32)
        grid_np = np.asarray(image_grid_thw, dtype=np.int64)
        positions_np = np.asarray(patch_positions, dtype=np.int64)
        expected_grid = np.repeat(
            np.asarray([[1, 14, 14]], dtype=np.int64), 4, axis=0
        )
        if grid_np.shape != (4, 3) or not np.array_equal(grid_np, expected_grid):
            raise ValueError(f"M269 image grid mismatch: {grid_np.tolist()}")
        if pixels_np.shape != (4 * 14 * 14, 768):
            raise ValueError(f"M269 pixel geometry mismatch: {pixels_np.shape}")
        if positions_np.shape != (4 * 14 * 14, 3):
            raise ValueError(f"M269 position geometry mismatch: {positions_np.shape}")

        self._vision_started = time.monotonic()
        print(
            "VISION_BEGIN layers=24 gemm_dtype=FP32 bf16_prefix=2 "
            "source_frames=2 views=4 frame_size=224 visual_tokens=196 "
            "w4_cache=M261-bounded-exact",
            flush=True,
        )
        passed = False
        try:
            torch = self.torch
            pixels = torch.from_numpy(pixels_np).to(self.compute_dtype)
            grid = torch.from_numpy(grid_np)
            positions = torch.from_numpy(positions_np)
            with torch.inference_mode():
                output = self.vision(
                    pixels, grid_thw=grid, patch_positions=positions
                ).last_hidden_state
            if list(output.shape) != [196, 2560] or not torch.isfinite(output).all():
                raise RuntimeError(
                    f"M269 multiscale visual output gate failed: {list(output.shape)}"
                )
            passed = True
            return output.float().cpu().numpy()
        finally:
            print(
                f"VISION_{'PASS' if passed else 'FAIL'} source_frames=2 views=4 "
                f"frame_size=224 total_ms={self._elapsed() * 1000.0:.3f} "
                f"rss_mib={_rss_mib():.1f}",
                flush=True,
            )
