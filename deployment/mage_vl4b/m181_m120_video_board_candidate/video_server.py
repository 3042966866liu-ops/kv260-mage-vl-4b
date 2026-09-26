#!/usr/bin/env python3
"""M120 KV260 four-frame video-to-SSE service; load is fail-closed."""

from __future__ import annotations

import argparse
import json
import sys
import threading
import time
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from board_preprocess import preprocess
from ps_vision_runtime import M90PSVisionRuntime, sha256
from video_language_runtime import EOS_ID, M120VideoLanguageModel, expected_physical_calls
from video_prompt import tokenize
from video_request import CONTENT_TYPE, FRAME_BYTES, HEADER, MAX_PROMPT_BYTES, decode


HERE = Path(__file__).resolve().parent
STATIC = HERE / "static"
MAX_BODY = HEADER.size + MAX_PROMPT_BYTES + FRAME_BYTES
BUILD_ID = "0x4D395832"
KERNEL = "mage_m120_m89x2_0"
LANGUAGE_MANIFEST = "12ea4b8cc58639d0aab6da4ef3a3f12bbbb1254f88865f76512a5f0d00d4ae5d"
HEAD_MANIFEST = "a1a555700e3daec8049627564c73e5783affe3827ab5437665249786d5c079ef"
VISION_MANIFEST = "2d9bea77b8868d24fa7775886feb1b9c88b8e768d51b2e192802a439060b03c1"


def read_json(path: Path) -> dict:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def offline_preflight(config: dict[str, Path]) -> dict:
    checks: dict[str, bool] = {}
    board_gate = read_json(config["board_gate"])
    fixed = board_gate.get("latest_m120_fixed_text_e2e")
    checks["m120_fixed_text_board_e2e"] = (
        isinstance(fixed, dict)
        and fixed.get("status") == "PASS"
        and str(fixed.get("build_id", "")).lower() == BUILD_ID.lower()
    )
    checks["stable_rollback_preserved"] = board_gate.get("stable_rollback_preserved") is True

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

    language_manifest = config["weights_root"] / "language_fourport/SIXPORT_LAYOUT_MANIFEST.json"
    head_manifest = config["weights_root"] / "lmhead_fourport/SIXPORT_LAYOUT_MANIFEST.json"
    vision_manifest = config["vision_layout"] / "SIXPORT_LAYOUT_MANIFEST.json"
    checks["m120_language_layout"] = language_manifest.is_file() and sha256(language_manifest) == LANGUAGE_MANIFEST
    checks["m120_lm_head_layout"] = head_manifest.is_file() and sha256(head_manifest) == HEAD_MANIFEST
    checks["immutable_vision_layout"] = vision_manifest.is_file() and sha256(vision_manifest) == VISION_MANIFEST

    required = (
        config["candidate"] / "text_runtime/overlay/m120_m89x2_t32.bit",
        config["candidate"] / "text_runtime/overlay/m120_m89x2_t32.hwh",
        config["candidate"] / "text_runtime/runtime/board_runtime.py",
        config["candidate"] / "text_runtime/runtime/support/reserved_ddr_pool.py",
        config["candidate"] / "text_runtime/contracts/M126_LANGUAGE_RUNTIME_CONTRACT_RESULT.json",
        config["candidate"] / "text_runtime/contracts/M126_LMHEAD_RUNTIME_CONTRACT_RESULT.json",
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
        "gate": "M152-M120-video-service-offline-preflight",
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
            runtime_root = self.config["candidate"] / "text_runtime/runtime"
            support_root = runtime_root / "support"
            sys.path.insert(0, str(support_root))
            sys.path.insert(0, str(runtime_root))
            from board_runtime import M120BoardRuntime
            from tokenizers import Tokenizer

            board = M120BoardRuntime(
                self.config["candidate"] / "text_runtime/overlay/m120_m89x2_t32.bit",
                self.config["weights_root"] / "language_fourport",
                self.config["weights_root"] / "lmhead_fourport",
                self.config["candidate"] / "text_runtime/contracts/M126_LANGUAGE_RUNTIME_CONTRACT_RESULT.json",
                self.config["candidate"] / "text_runtime/contracts/M126_LMHEAD_RUNTIME_CONTRACT_RESULT.json",
                weight_mode="staged-low-cma",
            )
            try:
                vision = M90PSVisionRuntime(
                    self.config["model_code"],
                    self.config["vision_layout"],
                    self.config["raw_vision_manifest"],
                )
                language = M120VideoLanguageModel(board, self.config["auxiliary"])
                tokenizer = Tokenizer.from_file(str(self.config["tokenizer"]))
            except Exception:
                board.close()
                raise
            self.board, self.vision, self.language, self.tokenizer = board, vision, language, tokenizer

    def health(self) -> dict:
        return {
            "status": "ready" if self.board is not None else "cold",
            "model": "microsoft/Mage-VL 4B",
            "backend": "KV260 PS BF16-W4 vision + M120/M89X2 FPGA T32 language/head",
            "build_id": BUILD_ID,
            "kernel": KERNEL,
            "fixed_video_contract": "4 decoded RGB frames, 448x448, timestamps 0/1/2/3 seconds",
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
            yield "stage", {"name": "vision", "label": "PS BF16-W4 视觉塔"}
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
                    "vision_backend": "PS BF16 activation + immutable exact W4 weights; visual A8 disabled",
                },
            }

    def close(self) -> None:
        if self.language is not None:
            self.language.close()
        if self.vision is not None:
            self.vision.close()
        if self.board is not None:
            self.board.close()


class Handler(BaseHTTPRequestHandler):
    server_version = "TeLLMeM120Video/1.0"

    @property
    def runtime(self) -> M120VideoRuntime:
        return self.server.runtime  # type: ignore[attr-defined]

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
        if self.path in ("/", "/index.html"):
            self.send_static("index.html", "text/html; charset=utf-8")
        elif self.path == "/app.js":
            self.send_static("app.js", "text/javascript; charset=utf-8")
        elif self.path == "/style.css":
            self.send_static("style.css", "text/css; charset=utf-8")
        elif self.path == "/api/health":
            self.send_json(HTTPStatus.OK, self.runtime.health())
        else:
            self.send_error(HTTPStatus.NOT_FOUND)

    def do_POST(self) -> None:
        if self.path != "/api/4b/video/stream":
            self.send_error(HTTPStatus.NOT_FOUND)
            return
        media_type = self.headers.get("Content-Type", "").split(";", 1)[0].strip().lower()
        if media_type != CONTENT_TYPE:
            self.send_json(HTTPStatus.UNSUPPORTED_MEDIA_TYPE, {"error": f"expected {CONTENT_TYPE}"})
            return
        try:
            length = int(self.headers.get("Content-Length", "-1"))
        except ValueError:
            length = -1
        if not HEADER.size + FRAME_BYTES + 1 <= length <= MAX_BODY:
            self.send_json(HTTPStatus.BAD_REQUEST, {"error": "request length is outside the fixed contract"})
            return
        try:
            request = decode(self.rfile.read(length))
        except ValueError as exc:
            self.send_json(HTTPStatus.BAD_REQUEST, {"error": str(exc)})
            return
        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", "text/event-stream; charset=utf-8")
        self.send_header("Cache-Control", "no-cache")
        self.send_header("Connection", "close")
        self.end_headers()
        try:
            for name, payload in self.runtime.stream(request):
                self.event(name, payload)
        except Exception as exc:
            self.event("error", {"error": f"{type(exc).__name__}: {exc}"})


def make_config(candidate: Path, weights_root: Path, board_gate: Path) -> dict[str, Path]:
    return {
        "candidate": candidate,
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
    parser.add_argument("--weights-root", type=Path, required=True)
    parser.add_argument("--board-gate", type=Path, required=True)
    parser.add_argument("--host", default="0.0.0.0")
    parser.add_argument("--port", type=int, default=8001)
    parser.add_argument("--preflight", action="store_true")
    parser.add_argument("--result", type=Path)
    args = parser.parse_args()
    config = make_config(args.candidate.resolve(), args.weights_root.resolve(), args.board_gate.resolve())
    if args.preflight:
        result = offline_preflight(config)
        if args.result:
            args.result.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        print("M152_VIDEO_SERVICE_PREFLIGHT_PASS" if result["status"] == "PASS" else "M152_VIDEO_SERVICE_PREFLIGHT_FAIL")
        print(json.dumps(result, indent=2, sort_keys=True))
        return 0 if result["status"] == "PASS" else 1
    runtime = M120VideoRuntime(config)
    server = ThreadingHTTPServer((args.host, args.port), Handler)
    server.runtime = runtime  # type: ignore[attr-defined]
    try:
        print(f"M152 video service listening on http://{args.host}:{args.port}", flush=True)
        server.serve_forever()
    finally:
        runtime.close()
        server.server_close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
