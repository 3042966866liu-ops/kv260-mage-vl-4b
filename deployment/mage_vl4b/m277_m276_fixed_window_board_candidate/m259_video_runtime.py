#!/usr/bin/env python3
"""M259 pre-vision keyframe reduction for alarm-triggered 4B review."""

from __future__ import annotations

import time

import numpy as np

import m222_video_server as _m222
from m259_variable_vision_runtime import M259VariableFramePSVisionRuntime

# M243 resolves this attribute lazily during load().  The patch is process-local
# and exists only when the isolated M259 entry point is selected.
_m222.M222PSVisionRuntime = M259VariableFramePSVisionRuntime

import m243_video_server as _m243  # noqa: E402
import video_server as _server  # noqa: E402
from keyframe_reducer import select_alarm_keyframes  # noqa: E402
from variable_video_contract import preprocess, tokenize  # noqa: E402
from video_language_runtime import HIDDEN, IMAGE_PAD_ID, MAX_CONTEXT, VOCAB  # noqa: E402


def variable_input_embeddings(language, token_ids, visual_tokens):
    ids = np.asarray(token_ids, dtype=np.int64)
    if (
        ids.ndim != 1
        or not 1 <= ids.size <= MAX_CONTEXT
        or ids.min() < 0
        or ids.max() >= VOCAB
    ):
        raise ValueError("M259 token IDs are outside the accepted context/vocabulary contract")
    visual = np.asarray(visual_tokens, dtype=np.float32)
    positions = np.flatnonzero(ids == IMAGE_PAD_ID)
    if positions.size not in (392, 588) or visual.shape != (positions.size, HIDDEN):
        raise ValueError(f"M259 visual/pad mismatch: {visual.shape}/{positions.size}")
    hidden = np.asarray(language.embedding[ids], dtype=np.float32).copy()
    hidden[positions] = visual
    return hidden


class M259PreVisionKeyframeRuntime(_m243.M243VideoRuntime):
    """Run both vision and language only on the selected alarm context frames."""

    review_frames_kept = 2

    def health(self) -> dict:
        value = super().health()
        value.update({
            "m259_prevision_keyframes": True,
            "m259_source_frames": 4,
            "m259_review_frames_kept": self.review_frames_kept,
            "m259_vision_state_policy": "BF16 layers 0-1; FP32 layers 2-23",
            "m259_semantic_accuracy_gate": "pending",
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
                keep=self.review_frames_kept,
                timestamps_seconds=(0.0, 1.0, 2.0, 3.0),
            )
            yield "stage", {
                "name": "preprocess",
                "label": "M259 最新报警帧 + 最大变化上下文帧预处理",
                "source_frames": 4,
                "selected_indices": list(selection.indices),
            }
            tensors = preprocess(selected_frames)
            yield "stage", {
                "name": "vision",
                "label": "M259 两帧 M222-W4 视觉塔；BF16 L0-1 / FP32 L2-23",
            }
            visual = self.vision(
                tensors["pixel_values"],
                tensors["image_grid_thw"],
                tensors["patch_positions"],
            )
            yield "stage", {
                "name": "prefill",
                "label": "M259 两帧 392 visual-token + M238/M241 T32 Prefill",
                "selected_indices": list(selection.indices),
            }
            ids = tokenize(
                self.config["tokenizer"], request.prompt, selection.timestamps_seconds
            )
            hidden = variable_input_embeddings(self.language, ids, visual)
            token, _logits, cache = self.language.prefill(hidden)
            generated: list[int] = []
            rendered = ""
            first_token_ms = (time.perf_counter() - started) * 1000.0
            for index in range(request.max_new_tokens):
                if index:
                    token, _logits = self.language.decode(generated[-1], cache)
                if token == _server.EOS_ID:
                    break
                generated.append(int(token))
                current = self.tokenizer.decode(generated, skip_special_tokens=True)
                delta = current[len(rendered):] if current.startswith(rendered) else current
                rendered = current
                if delta:
                    yield "token", {
                        "text": delta,
                        "token_id": int(token),
                        "generated_tokens": len(generated),
                    }
            if not generated:
                raise RuntimeError("M259 generated no non-EOS token")

            after = self.board.evidence()
            call_delta = int(after["logical_calls"]) - int(before["logical_calls"])
            macro_delta = int(after["logical_expected_macros"]) - int(
                before["logical_expected_macros"]
            )
            expected_calls = _server.expected_physical_calls(len(ids), len(generated))
            if not (
                str(after.get("build_id", "")).lower() == _server.BUILD_ID.lower()
                and call_delta == expected_calls
                and macro_delta > 0
            ):
                raise RuntimeError(
                    "M259 FPGA proof mismatch "
                    f"build={after.get('build_id')} calls={call_delta}/{expected_calls} "
                    f"macros={macro_delta}"
                )
            yield "complete", {
                "status": "PASS",
                "prompt_tokens": len(ids),
                "generated_tokens": len(generated),
                "first_token_ms": first_token_ms,
                "total_ms": (time.perf_counter() - started) * 1000.0,
                "selected_frame_indices": list(selection.indices),
                "proof": {
                    "result": "PASS",
                    "build_id": _server.BUILD_ID,
                    "kernel": _server.KERNEL,
                    "pl_logical_chain_calls": call_delta,
                    "expected_pl_logical_chain_calls": expected_calls,
                    "pl_expected_macros": macro_delta,
                    "language_cpu_linear_fallback": False,
                    "vision_backend": (
                        "M259 two-frame M222 W4; BF16 L0-1 / FP32 L2-23"
                    ),
                    "language_scheduler": (
                        "M238 T32 + M241 grouped-GQA/reference-RoPE"
                    ),
                    "m259_prevision_keyframes": True,
                    "m259_semantic_accuracy_gate": "required-before-promotion",
                },
            }


_server.M120VideoRuntime = M259PreVisionKeyframeRuntime
