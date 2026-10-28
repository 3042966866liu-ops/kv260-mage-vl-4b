#!/usr/bin/env python3
"""Variable 2-4 frame output contract for the selected M258 vision runtime."""

from __future__ import annotations

import time

import numpy as np

from m206_ps_vision_runtime import _rss_mib
from m258_vectorized_w4_runtime import M258SelectedPSVisionRuntime


class M259VariableFramePSVisionRuntime(M258SelectedPSVisionRuntime):
    """Execute unchanged visual math with a frame-count-derived output gate."""

    def __call__(self, pixel_values, image_grid_thw, patch_positions):
        pixels_np = np.asarray(pixel_values, dtype=np.float32)
        grid_np = np.asarray(image_grid_thw, dtype=np.int64)
        positions_np = np.asarray(patch_positions, dtype=np.int64)
        if grid_np.ndim != 2 or grid_np.shape[1] != 3:
            raise ValueError("M259 image_grid_thw must be N x 3")
        frame_count = int(grid_np.shape[0])
        if frame_count not in (2, 3, 4):
            raise ValueError("M259 supports exactly two to four frames")
        if pixels_np.shape != (frame_count * 28 * 28, 768):
            raise ValueError(f"M259 pixel geometry mismatch: {pixels_np.shape}")
        if positions_np.shape != (frame_count * 28 * 28, 3):
            raise ValueError(f"M259 position geometry mismatch: {positions_np.shape}")

        self._vision_started = time.monotonic()
        print(
            "VISION_BEGIN layers=24 gemm_dtype=FP32 bf16_prefix=2 "
            f"frames={frame_count} w4_storage=M222-unchanged",
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
            expected_shape = [frame_count * 196, 2560]
            if list(output.shape) != expected_shape or not torch.isfinite(output).all():
                raise RuntimeError(
                    f"M259 variable visual output gate failed: {list(output.shape)}"
                )
            passed = True
            return output.float().cpu().numpy()
        finally:
            print(
                f"VISION_{'PASS' if passed else 'FAIL'} "
                f"frames={frame_count} total_ms={self._elapsed() * 1000.0:.3f} "
                f"rss_mib={_rss_mib():.1f}",
                flush=True,
            )
