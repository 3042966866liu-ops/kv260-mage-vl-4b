#!/usr/bin/env python3
"""M243 Web service: M223/M227 stream runtime with accepted M241 Prefill."""

from __future__ import annotations

import sys

import m222_video_server as _m222
import video_server as _server
from m238_prefill_runtime import M238PrefillRuntime
from m241_video_language_runtime import M241VideoLanguageModel


class M243VideoRuntime(_m222.M222VideoRuntime):
    """Change only the language runtime/model selected by the accepted Web worker."""

    def load(self) -> None:
        if self.board is not None:
            return
        with self._load_lock:
            if self.board is not None:
                return
            result = _server.offline_preflight(self.config)
            if result["status"] != "PASS":
                raise RuntimeError(f"M243 offline preflight failed: {result['checks']}")
            runtime_root = self.config["text_candidate"] / "runtime"
            support_root = runtime_root / "support"
            sys.path.insert(0, str(support_root))
            sys.path.insert(0, str(runtime_root))
            from tokenizers import Tokenizer

            board = M238PrefillRuntime(
                self.config["text_candidate"] / "overlay/m120_m89x2_t32.bit",
                self.config["weights_root"] / "language_fourport",
                self.config["weights_root"] / "lmhead_fourport",
                self.config["text_candidate"] / "contracts/M126_LANGUAGE_RUNTIME_CONTRACT_RESULT.json",
                self.config["text_candidate"] / "contracts/M126_LMHEAD_RUNTIME_CONTRACT_RESULT.json",
                weight_mode="staged-low-cma",
            )
            try:
                vision = _m222.M222PSVisionRuntime(
                    self.config["model_code"],
                    self.config["vision_layout"],
                    self.config["raw_vision_manifest"],
                    progress_callback=self._publish_progress,
                )
                language = M241VideoLanguageModel(board, self.config["auxiliary"])
                tokenizer = Tokenizer.from_file(str(self.config["tokenizer"]))
            except Exception:
                board.close()
                raise
            self.board, self.vision, self.language, self.tokenizer = (
                board,
                vision,
                language,
                tokenizer,
            )

    def health(self) -> dict:
        value = super().health()
        value.update({
            "web_language_runtime": "M243-M238-T32-pack-prefetch-fused-parse",
            "web_prefill_attention": "M241-grouped-GQA-reference-RoPE",
            "web_prefill_hash_locked": True,
            "t64_used": False,
        })
        return value

    def stream(self, request):
        for name, payload in super().stream(request):
            payload = dict(payload)
            if name == "stage" and payload.get("name") == "prefill":
                payload["label"] = "FPGA T32 M238 调度 + M241 Grouped-GQA Prefill"
            if name == "complete" and isinstance(payload.get("proof"), dict):
                proof = dict(payload["proof"])
                proof.update({
                    "language_scheduler": "M238 T32 input-pack prefetch + fused parse overlap",
                    "prefill_attention": "M241 grouped-GQA with reference RoPE",
                    "t64_used": False,
                })
                payload["proof"] = proof
            yield name, payload


class M243ContinuousVideoEngine(_m222.M222ContinuousVideoEngine):
    """Expose the exact selected runtime classes through the accepted status API."""

    def status(self) -> dict:
        value = super().status()
        health = self.runtime.health()
        value.update({
            "web_runtime_class": type(self.runtime).__name__,
            "web_board_runtime_class": (
                type(self.runtime.board).__name__ if self.runtime.board is not None else None
            ),
            "web_language_model_class": (
                type(self.runtime.language).__name__ if self.runtime.language is not None else None
            ),
            "web_language_runtime": health.get("web_language_runtime"),
            "web_prefill_attention": health.get("web_prefill_attention"),
            "web_prefill_hash_locked": health.get("web_prefill_hash_locked"),
            "t64_used": health.get("t64_used"),
        })
        return value


# The accepted M223 main/handler resolve this global when creating a session.
_server.M120VideoRuntime = M243VideoRuntime
_server.ContinuousVideoEngine = M243ContinuousVideoEngine


if __name__ == "__main__":
    raise SystemExit(_server.main())
