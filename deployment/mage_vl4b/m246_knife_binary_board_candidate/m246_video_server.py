#!/usr/bin/env python3
"""M246: M243 Web runtime plus constrained one-token knife classification."""

from __future__ import annotations

import hashlib
import sys
import time

import numpy as np

import m243_video_server as _m243
import video_server as _server
from knife_alarm import KnifeAlarmStateMachine, KnifeObservation
from live_stream_core import EventJournal
from m246_knife_binary import (
    KNIFE_PROMPT,
    constrained_knife_decision,
    verify_tokenizer_contract,
)


class KnifeAlarmEventJournal(EventJournal):
    """Publish an alarm event immediately after each structured observation."""

    def __init__(self):
        super().__init__()
        self.machine = KnifeAlarmStateMachine()
        self.observation_count = 0

    def publish(self, name: str, payload: dict) -> dict:
        event = super().publish(name, payload)
        if name == "knife_observation":
            sequences = tuple(int(value) for value in payload["window_sequences"])
            observation = KnifeObservation(
                window_index=self.observation_count,
                sequences=sequences,
                evidence_sha256=str(payload["evidence_sha256"]),
                verdict=str(payload["verdict"]),
                score=float(payload["knife_score"]),
                raw_model_output=str(payload["text"]),
                captured_unix_ms=int(time.time() * 1000.0),
            )
            self.observation_count += 1
            alarm = self.machine.update(observation)
            alarm.update({
                "build_id": _server.BUILD_ID,
                "model": "microsoft/Mage-VL 4B",
                "classifier": "M246-constrained-token-15-vs-16",
            })
            super().publish("knife_alarm", alarm)
        return event


class M246KnifeVideoRuntime(_m243.M243VideoRuntime):
    """Use constrained decoding only for the exact knife classifier prompt."""

    def load(self) -> None:
        super().load()
        assert self.tokenizer is not None
        self.knife_tokenizer_contract = verify_tokenizer_contract(self.tokenizer)

    def health(self) -> dict:
        value = super().health()
        value.update({
            "knife_classifier": "M246-constrained-token-15-vs-16",
            "knife_prompt_hash_locked": True,
            "knife_score_calibrated": False,
        })
        return value

    def stream(self, request):
        if request.prompt != KNIFE_PROMPT:
            yield from super().stream(request)
            return

        self.load()
        assert self.board is not None and self.vision is not None
        assert self.language is not None and self.tokenizer is not None
        with self._inference_lock:
            before = self.board.evidence()
            started = time.perf_counter()
            yield "stage", {"name": "preprocess", "label": "四帧预处理"}
            tensors = _server.preprocess(request.frames_rgb_u8)
            yield "stage", {
                "name": "vision",
                "label": "M222 向量化 W4 解码 + M207 FP32 视觉塔",
            }
            visual = self.vision(
                tensors["pixel_values"], tensors["image_grid_thw"], tensors["patch_positions"]
            )
            yield "stage", {
                "name": "prefill",
                "label": "FPGA T32 M238 + M241；0/1 受限刀具判定",
            }
            ids = _server.tokenize(self.config["tokenizer"], request.prompt)
            hidden = self.language.input_embeddings(ids, visual)
            _raw_token, logits, _cache = self.language.prefill(hidden)
            decision = constrained_knife_decision(logits)
            first_token_ms = (time.perf_counter() - started) * 1000.0
            yield "token", {
                "text": decision["text"],
                "token_id": decision["token_id"],
                "generated_tokens": 1,
                "constrained": True,
            }
            evidence_sha256 = hashlib.sha256(
                np.ascontiguousarray(request.frames_rgb_u8).tobytes()
            ).hexdigest()
            yield "knife_observation", {
                **decision,
                "evidence_sha256": evidence_sha256,
                "thresholds_calibrated": False,
            }

            after = self.board.evidence()
            call_delta = int(after["logical_calls"]) - int(before["logical_calls"])
            macro_delta = (
                int(after["logical_expected_macros"])
                - int(before["logical_expected_macros"])
            )
            expected_calls = _server.expected_physical_calls(len(ids), 1)
            proof_pass = (
                str(after.get("build_id", "")).lower() == _server.BUILD_ID.lower()
                and call_delta == expected_calls
                and macro_delta > 0
            )
            if not proof_pass:
                raise RuntimeError(
                    "M246 FPGA proof mismatch "
                    f"build={after.get('build_id')} calls={call_delta}/{expected_calls} "
                    f"macros={macro_delta}"
                )
            yield "complete", {
                "status": "PASS",
                "prompt_tokens": len(ids),
                "generated_tokens": 1,
                "first_token_ms": first_token_ms,
                "total_ms": (time.perf_counter() - started) * 1000.0,
                "knife_decision": decision,
                "proof": {
                    "result": "PASS",
                    "build_id": _server.BUILD_ID,
                    "kernel": _server.KERNEL,
                    "pl_logical_chain_calls": call_delta,
                    "expected_pl_logical_chain_calls": expected_calls,
                    "pl_expected_macros": macro_delta,
                    "language_cpu_linear_fallback": False,
                    "language_scheduler": "M238 T32 input-pack prefetch + fused parse overlap",
                    "prefill_attention": "M241 grouped-GQA with reference RoPE",
                    "classifier": "M246 constrained 0/1 logits; no decode call",
                    "score_calibrated": False,
                },
            }


class M246KnifeContinuousVideoEngine(_m243.M243ContinuousVideoEngine):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.events = KnifeAlarmEventJournal()

    def status(self) -> dict:
        value = super().status()
        journal = self.events
        value.update({
            "knife_alarm_state": journal.machine.state,
            "knife_last_alarm_evidence": journal.machine.last_alarm_evidence,
            "knife_thresholds_calibrated": False,
            "knife_classifier": "M246-constrained-token-15-vs-16",
        })
        return value


_server.M120VideoRuntime = M246KnifeVideoRuntime
_server.ContinuousVideoEngine = M246KnifeContinuousVideoEngine


if __name__ == "__main__":
    raise SystemExit(_server.main())

