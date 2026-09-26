#!/usr/bin/env python3
"""Fixed text gate and same-session BACT video + OP01 Decode measurement.

Runs only from a versioned board runner after package and environment preflight.
The M277 visual input and M241 language math remain unchanged.  Candidate
Build 0x4F503131 uses legacy T32 mode for Prefill and OP01 mode for Decode.
"""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import os
import sys
import threading
import time
from pathlib import Path


ROOT = Path("/home/ubuntu/tellme_m120_m89x2_20260901")
SEQ = ROOT / "optimization_v1/OP01-decode-one-sequence-01"
M277 = ROOT / "m277_m276_fixed_window_candidate"
STABLE = ROOT / "m175_m120_fixed_text_candidate"
FRAMES = ROOT / "m249_ssdlite_board_candidate/fixtures"
M325 = Path(__file__).resolve().parent
BUILD = {"stable": 0x4D395832, "candidate": 0x4F503131}
M277_MANIFEST = "0e1bdfa578f655b2bb6d07b097f1dda115a7936906e3e112137123db65e7f2fa"
FRAMES_SHA256 = "5911485955780036ac4c8990bcaa248667f2e86bd1fd6f9b0783002553b4adff"
FRAME_NAMES = (
    "frame_00_0068_rgb448.npy", "frame_01_0102_rgb448.npy",
    "frame_02_0137_rgb448.npy", "frame_03_0171_rgb448.npy",
)


def digest_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def atomic_json(path: Path, value: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + f".partial-{os.getpid()}")
    temporary.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    os.replace(temporary, path)


def bind_runtime(mode: str):
    # Bind before importing M238/M241: their modules reference board_runtime.
    paths = [M277, M325, SEQ, ROOT / "m254_dual_path_web_candidate",
             ROOT / "m243_web_prefill_delta", ROOT / "m242_m241_fixed_text_delta",
             ROOT / "m227_runtime_base_patch", ROOT / "m223_realtime_delta",
             ROOT / "m218_dual_source_delta", ROOT / "m181_m120_video_board_candidate",
             ROOT / "m190_mage_runtime", STABLE / "runtime", STABLE / "runtime/support"]
    sys.path[1:1] = [str(path) for path in paths]
    source = SEQ / ("candidate_base.py" if mode == "candidate" else "stable_base.py")
    spec = importlib.util.spec_from_file_location("board_runtime", source)
    if spec is None or spec.loader is None:
        raise RuntimeError("board runtime module unavailable")
    base = importlib.util.module_from_spec(spec)
    sys.modules["board_runtime"] = base
    spec.loader.exec_module(base)
    if base.BUILD_ID != BUILD[mode]:
        raise RuntimeError("board runtime Build-ID mismatch")
    from m238_prefill_runtime import M238PrefillRuntime
    from m241_video_language_runtime import M241VideoLanguageModel
    from tokenizers import Tokenizer
    import video_server
    if mode == "candidate":
        from decode_one_policy import execution_config
        from m325_full_session_runtime import candidate_runtime_class
        runtime_type = candidate_runtime_class(M238PrefillRuntime, base, execution_config)
    else:
        runtime_type = M238PrefillRuntime
    return base, runtime_type, M241VideoLanguageModel, Tokenizer, video_server


def config_for(video_server):
    return video_server.make_config(
        ROOT / "m181_m120_video_board_candidate", STABLE,
        ROOT / "m120_fulltext_weights_0x4D395832",
        ROOT / "m223_realtime_delta/M223_PREDECESSOR_SUMMARY.json",
    )


def preflight_packages(config, video_server):
    from op01_support import verify_package
    from ps_vision_runtime import sha256
    verify_package(SEQ, "21d41a9589bef5bae080ff93ff78f57658766013c076e387bdbda90a1a03d6e0")
    build = M277 / "PACKAGE_MANIFEST.json"
    if not build.is_file() or sha256(build) != M277_MANIFEST:
        raise RuntimeError("M277 package manifest changed")
    result = video_server.offline_preflight(config)
    if result.get("status") != "PASS":
        raise RuntimeError(f"stable predecessor preflight failed: {result.get('checks')}")
    return M277_MANIFEST


def load_frames():
    import numpy as np
    frames = np.stack([np.load(FRAMES / name, allow_pickle=False) for name in FRAME_NAMES])
    if frames.shape != (4, 448, 448, 3) or frames.dtype != np.uint8:
        raise RuntimeError("M277 video fixture shape/dtype mismatch")
    return np.ascontiguousarray(frames)


def lengths(cache):
    return [int(value.shape[0]) for value in cache.keys + cache.values]


def run_model(args) -> dict:
    import numpy as np
    base, runtime_type, language_type, tokenizer_type, video_server = bind_runtime(args.mode)
    config = config_for(video_server)
    manifest = preflight_packages(config, video_server)
    from op01_support import guarded_close_board
    from video_language_runtime import EOS_ID
    board = language = vision = None
    launched = False
    result = {"gate": "M325-full-session-OP01", "status": "FAIL",
              "scope": args.scope, "mode": args.mode,
              "build_id": f"0x{BUILD[args.mode]:08X}",
              "capacity_status": "STOPPED_BY_USER_NOT_PASS" if args.mode == "candidate" else "stable",
              "formal_promotion_allowed": False if args.mode == "candidate" else True,
              "m277_manifest_sha256": manifest, "error": None}
    phase = ["runtime initialization"]
    done = threading.Event()

    def heartbeat():
        while not done.wait(30):
            print("M325_HEARTBEAT phase=" + phase[0], flush=True)

    threading.Thread(target=heartbeat, daemon=True).start()
    try:
        overlay = (SEQ / "overlay/op01_decode_one.bit" if args.mode == "candidate"
                   else STABLE / "overlay/m120_m89x2_t32.bit")
        board = runtime_type(
            overlay, ROOT / "m120_fulltext_weights_0x4D395832/language_fourport",
            ROOT / "m120_fulltext_weights_0x4D395832/lmhead_fourport",
            STABLE / "contracts/M126_LANGUAGE_RUNTIME_CONTRACT_RESULT.json",
            STABLE / "contracts/M126_LMHEAD_RUNTIME_CONTRACT_RESULT.json",
            weight_mode="staged-low-cma")
        language = language_type(board, config["auxiliary"])
        tokenizer = tokenizer_type.from_file(str(config["tokenizer"]))
        if args.scope == "video":
            from m273_latest_vision_runtime import M273LatestPSVisionRuntime
            vision = M273LatestPSVisionRuntime(
                config["model_code"], config["vision_layout"],
                config["raw_vision_manifest"], progress_callback=lambda *row: print(*row, flush=True))
        before = board.evidence()
        start = time.perf_counter()
        if args.scope == "text":
            prompt = "<|im_start|>user\nHello.<|im_end|>\n<|im_start|>assistant\n"
            ids = [int(x) for x in tokenizer.encode(prompt, add_special_tokens=False).ids]
            if not 1 <= len(ids) <= 32:
                raise RuntimeError("fixed text gate requires one T32 batch")
            hidden = np.asarray(language.embedding[ids], dtype=np.float32).copy()
            phase[0] = "fixed text Prefill"
            launched = True
            if args.mode == "candidate":
                with board.phase("prefill"):
                    token, logits, cache = language.prefill(hidden)
            else:
                token, logits, cache = language.prefill(hidden)
            ready = time.perf_counter()
            output_tokens = [int(token)]
            logits_list = [logits.copy()]
            stage_ms = {"text_prefill": (ready - start) * 1000.0}
            ready_times = [ready]
        else:
            from m276_prompt_contract import M276_KNIFE_PROMPT, preprocess, tokenize
            from m276_video_runtime import latest_input_embeddings
            from m246_knife_binary import constrained_knife_decision
            frames = load_frames()
            result["frames_sha256"] = digest_bytes(frames.tobytes())
            if result["frames_sha256"] != FRAMES_SHA256:
                raise RuntimeError("M277 video fixture changed")
            phase[0] = "BACT 159-token preprocessing"
            tensors = preprocess(np.ascontiguousarray(frames[-1:]))
            preprocessed = time.perf_counter()
            phase[0] = "M273 98-token vision"
            visual = vision(tensors["pixel_values"], tensors["image_grid_thw"], tensors["patch_positions"])
            vision_ready = time.perf_counter()
            ids = tokenize(config["tokenizer"], M276_KNIFE_PROMPT, 3.0)
            if len(ids) != 159 or visual.shape != (98, 2560):
                raise RuntimeError("BACT M276 input budget changed")
            hidden = latest_input_embeddings(language, ids, visual)
            phase[0] = "FPGA T32 Prefill"
            launched = True
            if args.mode == "candidate":
                with board.phase("prefill"):
                    raw_token, logits, cache = language.prefill(hidden)
            else:
                raw_token, logits, cache = language.prefill(hidden)
            decision = constrained_knife_decision(logits)
            token = int(decision["token_id"])
            first_ready = time.perf_counter()
            if token != 15:
                raise RuntimeError(f"M277 frozen first token changed: {token}")
            output_tokens = [token]
            logits_list = [logits.copy()]
            ready_times = [first_ready]
            stage_ms = {"preprocess": (preprocessed - start) * 1000.0,
                        "vision": (vision_ready - preprocessed) * 1000.0,
                        "prefill_to_first_token": (first_ready - vision_ready) * 1000.0}
            for index in range(3):
                phase[0] = f"incremental Decode {index + 1}/3"
                prior = lengths(cache)
                if prior != [len(ids) + index] * 72:
                    raise RuntimeError("KV length changed before Decode")
                if args.mode == "candidate":
                    with board.phase("decode"):
                        token, logits = language.decode(output_tokens[-1], cache)
                else:
                    token, logits = language.decode(output_tokens[-1], cache)
                ready = time.perf_counter()
                if lengths(cache) != [len(ids) + index + 1] * 72:
                    raise RuntimeError("KV did not grow by one")
                output_tokens.append(int(token))
                logits_list.append(logits.copy())
                ready_times.append(ready)
                print(f"M325_TOKEN_READY index={index + 2} token={token} elapsed_s={ready-start:.6f}", flush=True)
        after = board.evidence()
        from video_language_runtime import expected_physical_calls
        expected = expected_physical_calls(len(ids), len(output_tokens))
        calls = int(after["logical_calls"]) - int(before["logical_calls"])
        if calls != expected or int(after["logical_expected_macros"]) <= int(before["logical_expected_macros"]):
            raise RuntimeError(f"FPGA call proof mismatch {calls}/{expected}")
        result.update(status="PASS_EXPERIMENTAL" if args.mode == "candidate" else "PASS_REFERENCE",
                      prompt_tokens=len(ids), generated_tokens=len(output_tokens),
                      token_ids=output_tokens, eos_ids=[index for index, value in enumerate(output_tokens) if value == EOS_ID],
                      logits_sha256=[digest_bytes(value.tobytes()) for value in logits_list],
                      final_kv_sha256=[digest_bytes(value.tobytes()) for value in cache.keys + cache.values],
                      final_kv_length=lengths(cache), stage_ms=stage_ms,
                      first_token_ms=(ready_times[0] - start) * 1000.0,
                      token_ready_ms=[(value - start) * 1000.0 for value in ready_times],
                      decode_intervals_ms=[(ready_times[index] - ready_times[index - 1]) * 1000.0
                                           for index in range(1, len(ready_times))],
                      decode_tokens_per_second=(len(ready_times)-1)/(ready_times[-1]-ready_times[0])
                          if len(ready_times)>1 else None,
                      end_to_end_tokens_per_second=len(ready_times)/(ready_times[-1]-start),
                      logical_fpga_calls=calls, expected_logical_fpga_calls=expected,
                      board_evidence=after, model_load_excluded=True,
                      continuation_after_eos=bool(args.scope == "video" and any(value == EOS_ID for value in output_tokens[:-1])))
        if args.reference:
            reference = json.loads(args.reference.read_text(encoding="utf-8"))
            for field in ("scope", "prompt_tokens", "generated_tokens", "token_ids",
                          "logits_sha256", "final_kv_sha256", "logical_fpga_calls"):
                if result[field] != reference[field]:
                    raise RuntimeError("stable full-session mismatch: " + field)
            result["stable_reference_exact"] = True
    except BaseException as exc:
        result["status"] = "FAIL"
        result["error"] = f"{type(exc).__name__}: {exc}"
        result["failed_phase"] = phase[0]
    finally:
        done.set()
        if board is not None:
            cleanup = guarded_close_board(board, base.transaction_snapshot, launched)
            result["cleanup"] = cleanup
            if cleanup.get("recovery_required") or cleanup.get("errors"):
                result["status"] = "FAIL"
                result["error"] = (result["error"] or "") + " guarded close failed"
        if language is not None:
            try:
                language.close()
            except BaseException as exc:
                result["status"] = "FAIL"
                result["error"] = (result["error"] or "") + f" language close: {exc}"
        if vision is not None:
            try:
                vision.close()
            except BaseException as exc:
                result["status"] = "FAIL"
                result["error"] = (result["error"] or "") + f" vision close: {exc}"
        atomic_json(args.result, result)
        if not result.get("cleanup", {}).get("recovery_required", False):
            args.result.with_suffix(".safe").write_text("M325_CLEANUP_SAFE\n", encoding="ascii")
    print("__M325_FULL_RESULT_BEGIN__", flush=True)
    serial_result = {key: result.get(key) for key in (
        "gate", "status", "scope", "mode", "build_id", "capacity_status",
        "formal_promotion_allowed", "error", "failed_phase", "frames_sha256",
        "prompt_tokens", "generated_tokens", "token_ids", "eos_ids",
        "logits_sha256", "final_kv_sha256", "final_kv_length", "stage_ms",
        "first_token_ms", "token_ready_ms", "decode_intervals_ms",
        "decode_tokens_per_second", "end_to_end_tokens_per_second",
        "logical_fpga_calls", "expected_logical_fpga_calls",
        "stable_reference_exact", "model_load_excluded", "continuation_after_eos",
        "cleanup",
    ) if key in result}
    serial_result["full_board_result_sha256"] = digest_bytes(args.result.read_bytes())
    print(json.dumps(serial_result, ensure_ascii=False, separators=(",", ":")), flush=True)
    print("__M325_FULL_RESULT_END__", flush=True)
    print("M325_RESULT " + json.dumps({"status": result["status"], "mode": args.mode,
                                     "scope": args.scope, "first_token_ms": result.get("first_token_ms"),
                                     "decode_tokens_per_second": result.get("decode_tokens_per_second"),
                                     "error": result["error"]}, ensure_ascii=False), flush=True)
    return 0 if result["status"].startswith("PASS") else 1


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", choices=BUILD, required=True)
    parser.add_argument("--scope", choices=("text", "video"), required=True)
    parser.add_argument("--result", type=Path, required=True)
    parser.add_argument("--reference", type=Path)
    args = parser.parse_args()
    if args.result.exists() or args.result.resolve().is_relative_to(SEQ):
        parser.error("result must be new and outside immutable package")
    if args.reference and args.mode != "candidate":
        parser.error("reference is only for candidate")
    return run_model(args)


if __name__ == "__main__":
    raise SystemExit(main())
