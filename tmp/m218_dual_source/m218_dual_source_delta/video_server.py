#!/usr/bin/env python3
"""M218 KV260 latest-only camera and local-file-loop HTTP/SSE service."""

from __future__ import annotations

import argparse
import json
import os
import sys
import threading
import time
from urllib.parse import parse_qs, urlparse
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from board_preprocess import preprocess
from ps_vision_runtime import sha256
from live_stream_core import ContinuousVideoEngine
from m207_ps_vision_runtime import M207PSVisionRuntime
from video_language_runtime import EOS_ID, M120VideoLanguageModel, expected_physical_calls
from video_prompt import tokenize
from video_request import CONTENT_TYPE, FRAME_BYTES, HEADER, MAX_PROMPT_BYTES, decode


HERE = Path(__file__).resolve().parent
STATIC = Path(os.environ.get("M200_STATIC_ROOT", str(HERE / "static")))
MAX_BODY = HEADER.size + MAX_PROMPT_BYTES + FRAME_BYTES
FRAME_RGB_BYTES = 448 * 448 * 3
BUILD_ID = "0x4D395832"
KERNEL = "mage_m120_m89x2_0"
LANGUAGE_MANIFEST = "12ea4b8cc58639d0aab6da4ef3a3f12bbbb1254f88865f76512a5f0d00d4ae5d"
HEAD_MANIFEST = "a1a555700e3daec8049627564c73e5783affe3827ab5437665249786d5c079ef"
VISION_MANIFEST = "2d9bea77b8868d24fa7775886feb1b9c88b8e768d51b2e192802a439060b03c1"
TEXT_PACKAGE_MANIFEST = "406dcca340e4604baeb761445795391c43ec26bd99fa06ffae893d597b17414f"
FIXED_TEXT_RESULT_SHA = "3a798eafd2e66974774dcdcac39de86243830a6a4771eb182cd535220b4aacd3"


def read_json(path: Path) -> dict:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def offline_preflight(config: dict[str, Path]) -> dict:
    checks: dict[str, bool] = {}
    board_gate = read_json(config["board_gate"])
    summary_mode = board_gate.get("gate") in (
        "M212-live-predecessor-summary", "M218-dual-source-predecessor-summary"
    )
    fixed = board_gate.get("m179") if summary_mode else board_gate.get("latest_m120_fixed_text_board_gate")
    checks["m120_fixed_text_board_e2e"] = (
        isinstance(fixed, dict)
        and fixed.get("status") == "PASS"
        and str(fixed.get("candidate_build_id", "")).lower() == BUILD_ID.lower()
        and fixed.get("fpga_execution_proved") is True
        and fixed.get("cpu_linear_fallback") is False
        and fixed.get("formal_result_sha256") == FIXED_TEXT_RESULT_SHA
    )
    checks["stable_rollback_preserved"] = board_gate.get("stable_rollback_preserved") is True
    optimized_vision = board_gate.get("m198") if summary_mode else board_gate.get("latest_m198_ps_vision_optimization")
    checks["m198_optimized_ps_vision"] = (
        isinstance(optimized_vision, dict)
        and optimized_vision.get("status") == "PASS"
        and optimized_vision.get("candidate_build_id") == BUILD_ID
        and optimized_vision.get("fp32_encoder_layers") == list(range(6, 24))
    )
    m208 = board_gate.get("m208") if summary_mode else board_gate.get("latest_m208_ps_vision_board_gate")
    checks["m208_selected_real_board_vision"] = (
        isinstance(m208, dict)
        and m208.get("status") == "PASS"
        and m208.get("candidate_build_id") == BUILD_ID
        and float(m208.get("metrics", {}).get("cosine_similarity", 0.0)) >= 0.999
        and float(m208.get("metrics", {}).get("rmse", 1.0)) <= 0.05
        and int(m208.get("bf16_gemm_warning_count", -1)) == 0
    )
    m209 = board_gate.get("m209") if summary_mode else board_gate.get("latest_m209_continuous_stream_core")
    checks["m209_latest_only_scheduler"] = (
        isinstance(m209, dict)
        and str(m209.get("status", "")).startswith("OFFLINE_PASS")
        and m209.get("runtime_load_count") == 1
        and m209.get("last_window_sequences") == [60, 61, 62, 63]
    )

    candidate_manifest_path = config["candidate"] / "PACKAGE_MANIFEST.json"
    candidate_manifest = read_json(candidate_manifest_path)
    candidate_ready = read_json(config["candidate"] / "PACKAGE_READY.json")
    checks["clean_m120_video_candidate"] = (
        candidate_manifest.get("status") == "OFFLINE_PACKAGE_PASS_BOARD_NOT_EXECUTED"
        and candidate_manifest.get("build_id") == BUILD_ID
        and candidate_manifest.get("kernel") == KERNEL
        and candidate_manifest.get("forbidden_cache_path_count") == 0
    )
    checks["candidate_manifest_external_hash"] = (
        candidate_ready.get("status") == "READY"
        and candidate_ready.get("build_id") == BUILD_ID
        and sha256(candidate_manifest_path) == candidate_ready.get("package_manifest_sha256")
    )

    text_manifest_path = config["text_candidate"] / "PACKAGE_MANIFEST.json"
    text_manifest = read_json(text_manifest_path)
    checks["m175_text_runtime_package"] = (
        sha256(text_manifest_path) == TEXT_PACKAGE_MANIFEST
        and text_manifest.get("build_id") == BUILD_ID
    )

    language_manifest = config["weights_root"] / "language_fourport/SIXPORT_LAYOUT_MANIFEST.json"
    head_manifest = config["weights_root"] / "lmhead_fourport/SIXPORT_LAYOUT_MANIFEST.json"
    vision_manifest = config["vision_layout"] / "SIXPORT_LAYOUT_MANIFEST.json"
    checks["m120_language_layout"] = language_manifest.is_file() and sha256(language_manifest) == LANGUAGE_MANIFEST
    checks["m120_lm_head_layout"] = head_manifest.is_file() and sha256(head_manifest) == HEAD_MANIFEST
    checks["immutable_vision_layout"] = vision_manifest.is_file() and sha256(vision_manifest) == VISION_MANIFEST

    required = (
        config["text_candidate"] / "overlay/m120_m89x2_t32.bit",
        config["text_candidate"] / "overlay/m120_m89x2_t32.hwh",
        config["text_candidate"] / "runtime/board_runtime.py",
        config["text_candidate"] / "runtime/support/reserved_ddr_pool.py",
        config["text_candidate"] / "contracts/M126_LANGUAGE_RUNTIME_CONTRACT_RESULT.json",
        config["text_candidate"] / "contracts/M126_LMHEAD_RUNTIME_CONTRACT_RESULT.json",
        config["auxiliary"] / "M151_M120_TEXT_AUX_MANIFEST.json",
        config["tokenizer"],
        config["model_code"] / "config.json",
        config["model_code"] / "configuration_mage_vl.py",
        config["model_code"] / "modeling_mage_vl.py",
        config["raw_vision_manifest"],
    )
    checks["required_files_present"] = all(path.is_file() for path in required)
    passed = all(checks.values())
    return {
        "gate": "M200-M120-video-service-M197-vision-offline-preflight",
        "status": "PASS" if passed else "FAIL",
        "checks": checks,
        "build_id": BUILD_ID,
        "kernel": KERNEL,
        "deployed": False,
        "board_state_changed": False,
    }


class M120VideoRuntime:
    def __init__(self, config: dict[str, Path]):
        self.config = config
        self._load_lock = threading.Lock()
        self._inference_lock = threading.Lock()
        self.board = None
        self.vision = None
        self.language = None
        self.tokenizer = None

    def load(self) -> None:
        if self.board is not None:
            return
        with self._load_lock:
            if self.board is not None:
                return
            result = offline_preflight(self.config)
            if result["status"] != "PASS":
                raise RuntimeError(f"M152 offline preflight failed: {result['checks']}")
            runtime_root = self.config["text_candidate"] / "runtime"
            support_root = runtime_root / "support"
            sys.path.insert(0, str(support_root))
            sys.path.insert(0, str(runtime_root))
            from board_runtime import M120BoardRuntime
            from tokenizers import Tokenizer

            board = M120BoardRuntime(
                self.config["text_candidate"] / "overlay/m120_m89x2_t32.bit",
                self.config["weights_root"] / "language_fourport",
                self.config["weights_root"] / "lmhead_fourport",
                self.config["text_candidate"] / "contracts/M126_LANGUAGE_RUNTIME_CONTRACT_RESULT.json",
                self.config["text_candidate"] / "contracts/M126_LMHEAD_RUNTIME_CONTRACT_RESULT.json",
                weight_mode="staged-low-cma",
            )
            try:
                vision = M207PSVisionRuntime(
                    self.config["model_code"],
                    self.config["vision_layout"],
                    self.config["raw_vision_manifest"],
                    progress_callback=self._publish_progress,
                )
                language = M120VideoLanguageModel(board, self.config["auxiliary"])
                tokenizer = Tokenizer.from_file(str(self.config["tokenizer"]))
            except Exception:
                board.close()
                raise
            self.board, self.vision, self.language, self.tokenizer = board, vision, language, tokenizer

    def set_progress_callback(self, callback) -> None:
        self._progress_callback = callback

    def _publish_progress(self, name: str, payload: dict) -> None:
        callback = getattr(self, "_progress_callback", None)
        if callback is not None:
            callback(name, payload)

    def health(self) -> dict:
        return {
            "status": "ready" if self.board is not None else "cold",
            "model": "microsoft/Mage-VL 4B",
            "backend": "KV260 M207 PS W4: FP32 Linear with M198 boundaries + M120/M89X2 FPGA T32 language/head",
            "build_id": BUILD_ID,
            "kernel": KERNEL,
            "stream_contract": "unbounded browser camera/RTSP ingress; 16-frame ring; newest four only; one inference worker",
            "board_runtime_loaded": self.board is not None,
        }

    def stream(self, request):
        self.load()
        assert self.board is not None and self.vision is not None
        assert self.language is not None and self.tokenizer is not None
        with self._inference_lock:
            before = self.board.evidence()
            started = time.perf_counter()
            yield "stage", {"name": "preprocess", "label": "四帧预处理"}
            tensors = preprocess(request.frames_rgb_u8)
            yield "stage", {"name": "vision", "label": "M207 PS W4：FP32 Linear，保留 M198 精度边界"}
            visual = self.vision(
                tensors["pixel_values"], tensors["image_grid_thw"], tensors["patch_positions"]
            )
            yield "stage", {"name": "prefill", "label": "FPGA M120 T32 Prefill"}
            ids = tokenize(self.config["tokenizer"], request.prompt)
            hidden = self.language.input_embeddings(ids, visual)
            token, _logits, cache = self.language.prefill(hidden)
            generated: list[int] = []
            rendered = ""
            first_token_ms = (time.perf_counter() - started) * 1000.0
            for index in range(request.max_new_tokens):
                if index:
                    token, _logits = self.language.decode(generated[-1], cache)
                if token == EOS_ID:
                    break
                generated.append(int(token))
                current = self.tokenizer.decode(generated, skip_special_tokens=True)
                delta = current[len(rendered) :] if current.startswith(rendered) else current
                rendered = current
                if delta:
                    yield "token", {
                        "text": delta,
                        "token_id": int(token),
                        "generated_tokens": len(generated),
                    }
            if not generated:
                raise RuntimeError("M152 generated no non-EOS token")
            after = self.board.evidence()
            call_delta = int(after["logical_calls"]) - int(before["logical_calls"])
            macro_delta = int(after["logical_expected_macros"]) - int(before["logical_expected_macros"])
            expected_calls = expected_physical_calls(len(ids), len(generated))
            proof_pass = (
                str(after.get("build_id", "")).lower() == BUILD_ID.lower()
                and call_delta == expected_calls
                and macro_delta > 0
            )
            if not proof_pass:
                raise RuntimeError(
                    "M152 FPGA proof mismatch "
                    f"build={after.get('build_id')} calls={call_delta}/{expected_calls} macros={macro_delta}"
                )
            yield "complete", {
                "status": "PASS",
                "prompt_tokens": len(ids),
                "generated_tokens": len(generated),
                "first_token_ms": first_token_ms,
                "total_ms": (time.perf_counter() - started) * 1000.0,
                "proof": {
                    "result": "PASS",
                    "build_id": BUILD_ID,
                    "kernel": KERNEL,
                    "pl_logical_chain_calls": call_delta,
                    "expected_pl_logical_chain_calls": expected_calls,
                    "pl_expected_macros": macro_delta,
                    "language_cpu_linear_fallback": False,
                    "vision_backend": "PS immutable W4 weights; L0-5 BF16, L6-23 FP32 blocks with BF16 boundaries; visual A8 disabled",
                },
            }

    def close(self) -> None:
        if self.language is not None:
            self.language.close()
        if self.vision is not None:
            self.vision.close()
        if self.board is not None:
            self.board.close()


class LiveController:
    """Own exactly one latest-only session and never queue finite windows."""

    def __init__(self, runtime: M120VideoRuntime):
        self.runtime = runtime
        self._lock = threading.RLock()
        self.engine: ContinuousVideoEngine | None = None
        self.source_mode = "unselected"
        self.source_label = ""
        self.source_content_is_finite = False

    def start(self, prompt: str, max_new_tokens: int,
              source_mode: str = "browser-camera", source_label: str = "") -> dict:
        prompt = prompt.strip()
        if not prompt or len(prompt.encode("utf-8")) > MAX_PROMPT_BYTES:
            raise ValueError("prompt must contain 1..3000 UTF-8 bytes")
        if not 1 <= int(max_new_tokens) <= 128:
            raise ValueError("max_new_tokens must be 1..128")
        source_mode = str(source_mode).strip()
        if source_mode not in ("browser-camera", "uploaded-file-loop"):
            raise ValueError("source_mode must be browser-camera or uploaded-file-loop")
        source_label = str(source_label).strip()
        if len(source_label.encode("utf-8")) > 256:
            raise ValueError("source_label must be at most 256 UTF-8 bytes")
        with self._lock:
            if self.engine is not None:
                raise RuntimeError("a live session is already active")
            engine = ContinuousVideoEngine(
                self.runtime,
                prompt=prompt,
                max_new_tokens=int(max_new_tokens),
                buffer_capacity=16,
                window_size=4,
            )
            self.runtime.set_progress_callback(engine.events.publish)
            self.source_mode = source_mode
            self.source_label = source_label
            self.source_content_is_finite = source_mode == "uploaded-file-loop"
            self.engine = engine
            engine.start()
            return self.status()

    def submit(self, frame_rgb_u8) -> int:
        with self._lock:
            engine = self.engine
        if engine is None:
            raise RuntimeError("live session has not started")
        return engine.submit(frame_rgb_u8)

    def status(self) -> dict:
        with self._lock:
            engine = self.engine
        if engine is None:
            return {
                "status": "idle",
                "mode": "continuous-latest-only",
                "source_is_unbounded": True,
                "source_mode": self.source_mode,
                "source_label": self.source_label,
                "source_content_is_finite": self.source_content_is_finite,
                "board_runtime_loaded": False,
                "build_id": BUILD_ID,
                "kernel": KERNEL,
            }
        value = engine.status()
        value.update({
            "status": "running",
            "board_runtime_loaded": self.runtime.board is not None,
            "build_id": BUILD_ID,
            "kernel": KERNEL,
            "source_mode": self.source_mode,
            "source_label": self.source_label,
            "source_content_is_finite": self.source_content_is_finite,
        })
        return value

    def close(self) -> None:
        with self._lock:
            engine = self.engine
        if engine is not None:
            engine.close(timeout=30.0)


class Handler(BaseHTTPRequestHandler):
    server_version = "TeLLMeM212Live/1.0"

    @property
    def controller(self) -> LiveController:
        return self.server.controller  # type: ignore[attr-defined]

    def log_message(self, fmt: str, *args: object) -> None:
        print(f"[m120-video-web] {self.address_string()} {fmt % args}", flush=True)

    def send_json(self, status: HTTPStatus, payload: dict) -> None:
        raw = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(raw)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(raw)

    def send_static(self, name: str, content_type: str) -> None:
        path = STATIC / name
        if not path.is_file():
            self.send_error(HTTPStatus.NOT_FOUND)
            return
        raw = path.read_bytes()
        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(raw)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(raw)

    def event(self, name: str, payload: dict) -> None:
        raw = f"event: {name}\ndata: {json.dumps(payload, ensure_ascii=False)}\n\n".encode("utf-8")
        self.wfile.write(raw)
        self.wfile.flush()

    def do_GET(self) -> None:
        parsed = urlparse(self.path)
        if parsed.path in ("/", "/index.html"):
            self.send_static("index.html", "text/html; charset=utf-8")
        elif parsed.path == "/app.js":
            self.send_static("app.js", "text/javascript; charset=utf-8")
        elif parsed.path == "/style.css":
            self.send_static("style.css", "text/css; charset=utf-8")
        elif parsed.path in ("/api/health", "/api/4b/video/live/status"):
            self.send_json(HTTPStatus.OK, self.controller.status())
        elif parsed.path == "/api/4b/video/live/events":
            self.stream_events(parse_qs(parsed.query))
        else:
            self.send_error(HTTPStatus.NOT_FOUND)

    def do_POST(self) -> None:
        parsed = urlparse(self.path)
        if parsed.path == "/api/4b/video/live/start":
            self.start_live()
        elif parsed.path == "/api/4b/video/live/frame":
            self.accept_frame()
        else:
            self.send_error(HTTPStatus.NOT_FOUND)

    def start_live(self) -> None:
        try:
            length = int(self.headers.get("Content-Length", "-1"))
            if not 2 <= length <= 4096:
                raise ValueError("live start body is outside the bounded contract")
            value = json.loads(self.rfile.read(length).decode("utf-8"))
            status = self.controller.start(
                value["prompt"],
                int(value.get("max_new_tokens", 1)),
                source_mode=value.get("source_mode", "browser-camera"),
                source_label=value.get("source_label", ""),
            )
            self.send_json(HTTPStatus.ACCEPTED, status)
        except (ValueError, KeyError, json.JSONDecodeError) as exc:
            self.send_json(HTTPStatus.BAD_REQUEST, {"error": str(exc)})
        except RuntimeError as exc:
            self.send_json(HTTPStatus.CONFLICT, {"error": str(exc)})

    def accept_frame(self) -> None:
        media_type = self.headers.get("Content-Type", "").split(";", 1)[0].strip().lower()
        if media_type != "application/x-tellme-rgb448":
            self.send_json(HTTPStatus.UNSUPPORTED_MEDIA_TYPE, {
                "error": "expected application/x-tellme-rgb448"
            })
            return
        try:
            length = int(self.headers.get("Content-Length", "-1"))
        except ValueError:
            length = -1
        if length != FRAME_RGB_BYTES:
            self.send_json(HTTPStatus.BAD_REQUEST, {"error": "frame must be exact RGB 448x448x3"})
            return
        try:
            import numpy as np

            raw = self.rfile.read(length)
            if len(raw) != FRAME_RGB_BYTES:
                raise ValueError("truncated live frame")
            frame = np.frombuffer(raw, dtype=np.uint8).reshape(448, 448, 3)
            sequence = self.controller.submit(frame)
            self.send_json(HTTPStatus.ACCEPTED, {"accepted": True, "sequence": sequence})
        except (ValueError, RuntimeError) as exc:
            self.send_json(HTTPStatus.CONFLICT, {"error": str(exc)})

    def stream_events(self, query: dict) -> None:
        engine = self.controller.engine
        if engine is None:
            self.send_json(HTTPStatus.CONFLICT, {"error": "live session has not started"})
            return
        try:
            after = int(query.get("after", ["0"])[0])
        except ValueError:
            after = 0
        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", "text/event-stream; charset=utf-8")
        self.send_header("Cache-Control", "no-cache")
        self.send_header("Connection", "keep-alive")
        self.send_header("X-Accel-Buffering", "no")
        self.end_headers()
        try:
            while True:
                events = engine.events.wait_after(after, timeout=15.0)
                if not events:
                    self.wfile.write(b": keepalive\n\n")
                    self.wfile.flush()
                    continue
                for item in events:
                    after = int(item["id"])
                    raw = (
                        f"id: {after}\nevent: {item['name']}\n"
                        f"data: {json.dumps(item['payload'], ensure_ascii=False)}\n\n"
                    ).encode("utf-8")
                    self.wfile.write(raw)
                    self.wfile.flush()
        except (BrokenPipeError, ConnectionResetError):
            return


def make_config(candidate: Path, text_candidate: Path, weights_root: Path, board_gate: Path) -> dict[str, Path]:
    return {
        "candidate": candidate,
        "text_candidate": text_candidate,
        "board_gate": board_gate,
        "weights_root": weights_root,
        "vision_layout": candidate / "vision_layout",
        "raw_vision_manifest": candidate / "auxiliary/M90_VISION_RAW_AUX_MANIFEST.json",
        "auxiliary": candidate / "text_auxiliary",
        "tokenizer": candidate / "text_auxiliary/tokenizer/tokenizer.json",
        "model_code": candidate / "ps_vision_payload",
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--candidate", type=Path, default=HERE)
    parser.add_argument("--text-candidate", type=Path, required=True)
    parser.add_argument("--weights-root", type=Path, required=True)
    parser.add_argument("--board-gate", type=Path, required=True)
    parser.add_argument("--host", default="0.0.0.0")
    parser.add_argument("--port", type=int, default=8001)
    parser.add_argument("--preflight", action="store_true")
    parser.add_argument("--result", type=Path)
    args = parser.parse_args()
    config = make_config(
        args.candidate.resolve(), args.text_candidate.resolve(),
        args.weights_root.resolve(), args.board_gate.resolve()
    )
    if args.preflight:
        result = offline_preflight(config)
        if args.result:
            args.result.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        print("M200_VIDEO_SERVICE_PREFLIGHT_PASS" if result["status"] == "PASS" else "M200_VIDEO_SERVICE_PREFLIGHT_FAIL")
        print(json.dumps(result, indent=2, sort_keys=True))
        return 0 if result["status"] == "PASS" else 1
    runtime = M120VideoRuntime(config)
    controller = LiveController(runtime)
    server = ThreadingHTTPServer((args.host, args.port), Handler)
    server.controller = controller  # type: ignore[attr-defined]
    try:
        print(f"M218 dual-source video service listening on http://{args.host}:{args.port}", flush=True)
        server.serve_forever()
    finally:
        controller.close()
        server.server_close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
