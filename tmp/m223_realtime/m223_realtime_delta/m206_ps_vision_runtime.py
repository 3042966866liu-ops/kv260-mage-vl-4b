#!/usr/bin/env python3
"""M206 progress-visible FP32-compute/BF16-boundary PS vision candidate."""

from __future__ import annotations

import threading
import time

try:
    import resource
except ModuleNotFoundError:  # Windows-only source/HTTP contract tests.
    resource = None

import ps_vision_runtime as _base


def _rss_mib() -> float:
    if resource is None:
        return 0.0
    return resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024.0


class M206ProgressLayer(_base._TorchModule):
    """Observe one encoder layer without changing its inputs or outputs."""

    def __init__(self, layer, index: int, heartbeat_seconds: float, run_elapsed,
                 dtype_label: str = "FP32", progress_callback=None):
        super().__init__()
        self.layer = layer
        self.index = int(index)
        self.heartbeat_seconds = float(heartbeat_seconds)
        self.run_elapsed = run_elapsed
        self.dtype_label = str(dtype_label)
        self.progress_callback = progress_callback

    def _emit(self, name: str, payload: dict) -> None:
        if self.progress_callback is not None:
            self.progress_callback(name, payload)

    def forward(self, *args, **kwargs):
        started = time.monotonic()
        stopped = threading.Event()
        print(
            f"VISION_LAYER_BEGIN index={self.index} dtype={self.dtype_label} "
            f"elapsed_s={self.run_elapsed():.3f} rss_mib={_rss_mib():.1f}",
            flush=True,
        )
        self._emit("vision_layer_begin", {
            "index": self.index,
            "total_layers": 24,
            "dtype": self.dtype_label,
            "elapsed_s": self.run_elapsed(),
            "rss_mib": _rss_mib(),
        })

        def heartbeat() -> None:
            while not stopped.wait(self.heartbeat_seconds):
                print(
                    f"VISION_HEARTBEAT layer={self.index} "
                    f"elapsed_s={self.run_elapsed():.3f} "
                    f"layer_elapsed_s={time.monotonic() - started:.3f} "
                    f"process_alive=true rss_mib={_rss_mib():.1f}",
                    flush=True,
                )
                self._emit("vision_heartbeat", {
                    "index": self.index,
                    "total_layers": 24,
                    "elapsed_s": self.run_elapsed(),
                    "layer_elapsed_s": time.monotonic() - started,
                    "rss_mib": _rss_mib(),
                    "process_alive": True,
                })

        worker = threading.Thread(
            target=heartbeat,
            name=f"m206-vision-heartbeat-{self.index}",
            daemon=True,
        )
        worker.start()
        passed = False
        try:
            output = self.layer(*args, **kwargs)
            passed = True
            return output
        finally:
            stopped.set()
            worker.join(timeout=min(1.0, self.heartbeat_seconds))
            label = "PASS" if passed else "FAIL"
            print(
                f"VISION_LAYER_{label} index={self.index} "
                f"layer_ms={(time.monotonic() - started) * 1000.0:.3f} "
                f"elapsed_s={self.run_elapsed():.3f} rss_mib={_rss_mib():.1f}",
                flush=True,
            )
            self._emit("vision_layer_pass" if passed else "vision_layer_fail", {
                "index": self.index,
                "total_layers": 24,
                "layer_ms": (time.monotonic() - started) * 1000.0,
                "elapsed_s": self.run_elapsed(),
                "rss_mib": _rss_mib(),
            })


class M206PSVisionRuntime(_base.M90PSVisionRuntime):
    """All visual compute in FP32, with BF16 state at explicit boundaries."""

    FP32_COMPONENTS = ("embeddings", "layernorm_pre", "layernorm_post", "merger")
    FP32_LAYERS = tuple(range(24))

    def __init__(self, model_code_root, layout_root, raw_manifest_path,
                 heartbeat_seconds: float = 30.0):
        self._vision_started = None
        super().__init__(
            model_code_root,
            layout_root,
            raw_manifest_path,
            compute="bf16",
            fp32_layers=self.FP32_LAYERS,
            fp32_components=self.FP32_COMPONENTS,
        )
        for index, layer in enumerate(self.vision.encoder.layers):
            self.vision.encoder.layers[index] = M206ProgressLayer(
                layer,
                index=index,
                heartbeat_seconds=heartbeat_seconds,
                run_elapsed=self._elapsed,
            )

    def _elapsed(self) -> float:
        return 0.0 if self._vision_started is None else time.monotonic() - self._vision_started

    def __call__(self, pixel_values, image_grid_thw, patch_positions):
        self._vision_started = time.monotonic()
        print(
            "VISION_BEGIN layers=24 gemm_dtype=FP32 state_dtype=BF16 "
            "w4_storage=unchanged",
            flush=True,
        )
        passed = False
        try:
            output = super().__call__(pixel_values, image_grid_thw, patch_positions)
            passed = True
            return output
        finally:
            label = "PASS" if passed else "FAIL"
            print(
                f"VISION_{label} total_ms={self._elapsed() * 1000.0:.3f} "
                f"rss_mib={_rss_mib():.1f}",
                flush=True,
            )
