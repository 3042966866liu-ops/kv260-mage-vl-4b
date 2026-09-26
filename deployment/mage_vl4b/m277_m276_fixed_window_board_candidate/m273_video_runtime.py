#!/usr/bin/env python3
"""M273 latest-alarm-frame exact multiscale constrained-binary runtime."""

from __future__ import annotations

import time

import numpy as np

import m222_video_server as _m222
import m259_video_runtime as _m259
import video_server as _server
from m246_knife_binary import constrained_knife_decision
from m273_latest_multiscale_contract import M273_KNIFE_PROMPT, preprocess, tokenize
from m273_latest_vision_runtime import M273LatestPSVisionRuntime
from video_language_runtime import HIDDEN, IMAGE_PAD_ID, MAX_CONTEXT, VOCAB


def latest_input_embeddings(language, token_ids, visual_tokens):
    ids = np.asarray(token_ids, dtype=np.int64)
    if ids.ndim != 1 or not 1 <= ids.size <= MAX_CONTEXT or ids.min() < 0 or ids.max() >= VOCAB:
        raise ValueError("M273 token IDs are outside the accepted contract")
    visual = np.asarray(visual_tokens, dtype=np.float32)
    positions = np.flatnonzero(ids == IMAGE_PAD_ID)
    if positions.size != 98 or visual.shape != (98, HIDDEN):
        raise ValueError(f"M273 visual/pad mismatch: {visual.shape}/{positions.size}")
    hidden = np.asarray(language.embedding[ids], dtype=np.float32).copy()
    hidden[positions] = visual
    return hidden


_m222.M222PSVisionRuntime = M273LatestPSVisionRuntime


class M273LatestBinaryRuntime(_m259.M259PreVisionKeyframeRuntime):
    def health(self) -> dict:
        value = super().health()
        value.update({
            "m273_latest_binary_review": True,
            "m273_source_frames": 1,
            "m273_views": 2,
            "m273_visual_tokens": 98,
            "m273_decode_calls": 0,
            "m273_prompt": "M273-constrained-knife-binary-v2",
            "m273_semantic_accuracy_gate": "small-suite-pass-board-pending",
        })
        return value

    def stream(self, request):
        self.load()
        assert self.board is not None and self.vision is not None
        assert self.language is not None and self.tokenizer is not None
        with self._inference_lock:
            before = self.board.evidence()
            started = time.perf_counter()
            source_frames = np.asarray(request.frames_rgb_u8)
            if source_frames.shape != (4, 448, 448, 3) or source_frames.dtype != np.uint8:
                raise ValueError("M273 requires a four-frame uint8 RGB448 source window")
            latest = np.ascontiguousarray(source_frames[-1:])
            yield "stage", {
                "name": "preprocess",
                "label": "M273 最新报警帧生成 224 全景 + 224 中心细节",
                "source_frames": 4,
                "selected_indices": [3],
            }
            tensors = preprocess(latest)
            yield "stage", {
                "name": "vision",
                "label": "M273 两视图 98-token M261 精确限额缓存视觉塔",
            }
            visual = self.vision(
                tensors["pixel_values"], tensors["image_grid_thw"], tensors["patch_positions"]
            )
            yield "stage", {
                "name": "prefill",
                "label": "M273 V2 受限 0/1 + M238/M241 T32 Prefill；无 Decode",
                "selected_indices": [3],
            }
            ids = tokenize(self.config["tokenizer"], M273_KNIFE_PROMPT, 3.0)
            hidden = latest_input_embeddings(self.language, ids, visual)
            _argmax_token, logits, _cache = self.language.prefill(hidden)
            decision = constrained_knife_decision(logits)
            token = int(decision["token_id"])
            first_token_ms = (time.perf_counter() - started) * 1000.0
            yield "token", {
                "text": decision["text"],
                "token_id": token,
                "generated_tokens": 1,
                "knife_verdict": decision["verdict"],
                "knife_score": decision["knife_score"],
                "score_calibrated": False,
            }
            after = self.board.evidence()
            call_delta = int(after["logical_calls"]) - int(before["logical_calls"])
            macro_delta = int(after["logical_expected_macros"]) - int(before["logical_expected_macros"])
            expected_calls = _server.expected_physical_calls(len(ids), 1)
            if not (
                str(after.get("build_id", "")).lower() == _server.BUILD_ID.lower()
                and call_delta == expected_calls and macro_delta > 0
            ):
                raise RuntimeError(
                    "M273 FPGA proof mismatch "
                    f"build={after.get('build_id')} calls={call_delta}/{expected_calls} macros={macro_delta}"
                )
            yield "knife_observation", {
                "verdict": decision["verdict"],
                "knife_score": decision["knife_score"],
                "score_kind": decision["score_kind"],
                "score_calibrated": False,
                "selected_frame_indices": [3],
            }
            yield "complete", {
                "status": "PASS",
                "prompt_tokens": len(ids),
                "generated_tokens": 1,
                "decode_calls": 0,
                "first_token_ms": first_token_ms,
                "total_ms": (time.perf_counter() - started) * 1000.0,
                "selected_frame_indices": [3],
                "knife_verdict": decision["verdict"],
                "knife_score": decision["knife_score"],
                "proof": {
                    "result": "PASS",
                    "build_id": _server.BUILD_ID,
                    "kernel": _server.KERNEL,
                    "pl_logical_chain_calls": call_delta,
                    "expected_pl_logical_chain_calls": expected_calls,
                    "pl_expected_macros": macro_delta,
                    "language_cpu_linear_fallback": False,
                    "vision_backend": "M273 latest global/detail M261 exact bounded W4 cache",
                    "language_scheduler": "M238 T32 + M241 grouped-GQA/reference-RoPE",
                    "knife_decision": "M273 constrained logits 0/1 V2",
                    "decode_calls": 0,
                },
            }


_server.M120VideoRuntime = M273LatestBinaryRuntime
