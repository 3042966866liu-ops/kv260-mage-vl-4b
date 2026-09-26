#!/usr/bin/env python3
"""M269 two-keyframe multiscale constrained-binary 4B review runtime."""

from __future__ import annotations

import time

import numpy as np

import m222_video_server as _m222
import m259_video_runtime as _m259
import video_server as _server
from keyframe_reducer import select_alarm_keyframes
from m246_knife_binary import constrained_knife_decision
from m269_multiscale_contract import preprocess, tokenize
from m269_multiscale_vision_runtime import M269MultiscalePSVisionRuntime
from video_language_runtime import HIDDEN, IMAGE_PAD_ID, MAX_CONTEXT, VOCAB


def multiscale_input_embeddings(language, token_ids, visual_tokens):
    ids = np.asarray(token_ids, dtype=np.int64)
    if (
        ids.ndim != 1
        or not 1 <= ids.size <= MAX_CONTEXT
        or ids.min() < 0
        or ids.max() >= VOCAB
    ):
        raise ValueError("M269 token IDs are outside the accepted contract")
    visual = np.asarray(visual_tokens, dtype=np.float32)
    positions = np.flatnonzero(ids == IMAGE_PAD_ID)
    if positions.size != 196 or visual.shape != (196, HIDDEN):
        raise ValueError(f"M269 visual/pad mismatch: {visual.shape}/{positions.size}")
    hidden = np.asarray(language.embedding[ids], dtype=np.float32).copy()
    hidden[positions] = visual
    return hidden


_m222.M222PSVisionRuntime = M269MultiscalePSVisionRuntime


class M269MultiscaleBinaryRuntime(_m259.M259PreVisionKeyframeRuntime):
    """Run four global/detail views and return the constrained 0/1 prefill decision."""

    def health(self) -> dict:
        value = super().health()
        value.update({
            "m269_multiscale_binary_review": True,
            "m269_source_keyframes": 2,
            "m269_views": 4,
            "m269_view_size": 224,
            "m269_visual_tokens": 196,
            "m269_decode_calls": 0,
            "m269_prompt": "M246-constrained-knife-binary-v1",
            "m269_semantic_accuracy_gate": "small-suite-pass-board-pending",
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
            selected_frames, selection = select_alarm_keyframes(
                source_frames,
                keep=2,
                timestamps_seconds=(0.0, 1.0, 2.0, 3.0),
            )
            yield "stage", {
                "name": "preprocess",
                "label": "M269 两关键帧生成 224 全景 + 224 中心细节四视图",
                "source_frames": 4,
                "selected_indices": list(selection.indices),
            }
            tensors = preprocess(selected_frames)
            yield "stage", {
                "name": "vision",
                "label": "M269 四视图 196-token M261 精确限额缓存视觉塔",
            }
            visual = self.vision(
                tensors["pixel_values"],
                tensors["image_grid_thw"],
                tensors["patch_positions"],
            )
            yield "stage", {
                "name": "prefill",
                "label": "M269 M246 受限 0/1 + M238/M241 T32 Prefill；无 Decode",
                "selected_indices": list(selection.indices),
            }
            ids = tokenize(
                self.config["tokenizer"], request.prompt, selection.timestamps_seconds
            )
            hidden = multiscale_input_embeddings(self.language, ids, visual)
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
            macro_delta = int(after["logical_expected_macros"]) - int(
                before["logical_expected_macros"]
            )
            expected_calls = _server.expected_physical_calls(len(ids), 1)
            if not (
                str(after.get("build_id", "")).lower() == _server.BUILD_ID.lower()
                and call_delta == expected_calls
                and macro_delta > 0
            ):
                raise RuntimeError(
                    "M269 FPGA proof mismatch "
                    f"build={after.get('build_id')} calls={call_delta}/{expected_calls} "
                    f"macros={macro_delta}"
                )
            yield "knife_observation", {
                "verdict": decision["verdict"],
                "knife_score": decision["knife_score"],
                "score_kind": decision["score_kind"],
                "score_calibrated": False,
                "selected_frame_indices": list(selection.indices),
            }
            yield "complete", {
                "status": "PASS",
                "prompt_tokens": len(ids),
                "generated_tokens": 1,
                "decode_calls": 0,
                "first_token_ms": first_token_ms,
                "total_ms": (time.perf_counter() - started) * 1000.0,
                "selected_frame_indices": list(selection.indices),
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
                    "vision_backend": (
                        "M269 four-view 224 M261 exact bounded W4 cache; "
                        "BF16 L0-1 / FP32 L2-23"
                    ),
                    "language_scheduler": "M238 T32 + M241 grouped-GQA/reference-RoPE",
                    "knife_decision": "M246 constrained logits 0/1",
                    "decode_calls": 0,
                },
            }


_server.M120VideoRuntime = M269MultiscaleBinaryRuntime
