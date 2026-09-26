#!/usr/bin/env python3
"""Prove that the packaged visual base accepts the M207 precision policy."""

import inspect

import ps_vision_runtime
from m207_ps_vision_runtime import M207PSVisionRuntime
from m222_vectorized_w4_runtime import M222PSVisionRuntime


parameters = inspect.signature(ps_vision_runtime.M90PSVisionRuntime.__init__).parameters
if "fp32_layers" not in parameters or "fp32_components" not in parameters:
    raise RuntimeError("M227 incompatible ps_vision_runtime base")
if not issubclass(M222PSVisionRuntime, M207PSVisionRuntime):
    raise RuntimeError("M227 M222/M207 inheritance mismatch")
print("M227_VISUAL_RUNTIME_IMPORT_PREFLIGHT_PASS")

