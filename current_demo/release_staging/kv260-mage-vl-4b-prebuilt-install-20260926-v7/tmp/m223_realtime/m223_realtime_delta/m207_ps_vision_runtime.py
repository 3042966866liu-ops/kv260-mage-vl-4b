#!/usr/bin/env python3
"""M207: FP32 W4 GEMM with the accepted M198 block precision policy."""

from __future__ import annotations

import time

import ps_vision_runtime as _base
from m206_ps_vision_runtime import M206ProgressLayer, _rss_mib


class M207FP32GemmW4Linear(_base._TorchModule):
    """Decode and multiply in FP32, then restore the caller's state dtype."""

    def __init__(self, torch, store, name: str, in_features: int,
                 out_features: int, has_bias: bool, compute_dtype):
        super().__init__()
        self.store = store
        self.name = name
        self.in_features = int(in_features)
        self.out_features = int(out_features)
        self.output_dtype = compute_dtype
        if has_bias:
            self.bias = torch.nn.Parameter(
                torch.empty(out_features, device="meta"), requires_grad=False
            )
        else:
            self.register_parameter("bias", None)

    def forward(self, values):
        import torch

        weight = torch.from_numpy(self.store.decode(self.name))
        bias = self.bias
        if self.output_dtype == torch.bfloat16:
            # Preserve the accepted M198 operand values while avoiding a BF16
            # GEMM dispatch on Cortex-A53: round once to BF16, then perform the
            # multiply/accumulate in native FP32.
            weight = weight.to(torch.bfloat16).to(torch.float32)
            values = values.to(torch.bfloat16).to(torch.float32)
            bias = bias.to(torch.bfloat16).to(torch.float32) if bias is not None else None
        else:
            weight = weight.to(torch.float32)
            values = values.to(torch.float32)
            bias = bias.to(torch.float32) if bias is not None else None
        output = torch.nn.functional.linear(values, weight, bias)
        return output.to(self.output_dtype)


class M207PSVisionRuntime(_base.M90PSVisionRuntime):
    """M198 precision topology with every W4 Linear GEMM forced to FP32."""

    FP32_LAYERS = tuple(range(6, 24))

    def __init__(self, model_code_root, layout_root, raw_manifest_path,
                 heartbeat_seconds: float = 30.0, progress_callback=None):
        self._vision_started = None
        original_linear = _base.M90LazyW4Linear
        _base.M90LazyW4Linear = M207FP32GemmW4Linear
        try:
            super().__init__(
                model_code_root,
                layout_root,
                raw_manifest_path,
                compute="bf16",
                fp32_layers=self.FP32_LAYERS,
            )
        finally:
            _base.M90LazyW4Linear = original_linear
        for index, layer in enumerate(self.vision.encoder.layers):
            self.vision.encoder.layers[index] = M206ProgressLayer(
                layer,
                index=index,
                heartbeat_seconds=heartbeat_seconds,
                run_elapsed=self._elapsed,
                dtype_label=(
                    "BF16_BLOCK_FP32_LINEAR" if index < 6
                    else "FP32_BLOCK_FP32_LINEAR"
                ),
                progress_callback=progress_callback,
            )

    def _elapsed(self) -> float:
        return 0.0 if self._vision_started is None else time.monotonic() - self._vision_started

    def __call__(self, pixel_values, image_grid_thw, patch_positions):
        self._vision_started = time.monotonic()
        print(
            "VISION_BEGIN layers=24 gemm_dtype=FP32 state_policy=M198 "
            "l00_05=BF16 l06_23=FP32 boundary=BF16 w4_storage=unchanged",
            flush=True,
        )
        passed = False
        try:
            output = super().__call__(pixel_values, image_grid_thw, patch_positions)
            passed = True
            return output
        finally:
            print(
                f"VISION_{'PASS' if passed else 'FAIL'} "
                f"total_ms={self._elapsed() * 1000.0:.3f} rss_mib={_rss_mib():.1f}",
                flush=True,
            )
