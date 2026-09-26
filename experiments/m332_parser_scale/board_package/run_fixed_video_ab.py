#!/usr/bin/env python3
"""M332 isolated A/B of the frozen M328 four-frame FPGA video inference."""

from __future__ import annotations

import ast
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import signal
import socket
import subprocess
import sys
import threading
import time


sys.dont_write_bytecode = True
PACKAGE = Path(__file__).resolve().parent
ADDON = Path("/home/ubuntu/tellme_release_video_addon_20260926_v3")
RELEASE = Path("/home/ubuntu/tellme_release_install_20260926")
VARIANT = os.environ.get("M332_VARIANT", "")
PREFLIGHT_ONLY = os.environ.get("M332_PREFLIGHT_ONLY", "0") == "1"
M332_SOURCE = PACKAGE / "m236_prefill_runtime.py"
M332_SOURCE_SHA = "7e36223f762cfc04c0fc74e3f468664e05d38b8f8024c8eb194e77cdc12944e8"
STABLE_M236_SHA = "d8061b561fe4d2a089523fde0d3860684244e76bca9646f255f03134fb50be56"
MANIFEST_SHA = "fc69e69c0396e29e06d4852b06f680b2365cb31fdd1ffb036b0f85037b6f6d6e"
M277_SHA = "0e1bdfa578f655b2bb6d07b097f1dda115a7936906e3e112137123db65e7f2fa"
FRAMES = {
    "frame_00_0068_rgb448.npy": "efbd192266329db17ab9b233b854fa4086a16ccf8faf8aace75462c164844e8f",
    "frame_01_0102_rgb448.npy": "e334ea6bdeb142a42a443afe27fa8af551895d568149ab8aca92a181fdc69243",
    "frame_02_0137_rgb448.npy": "81ddb1f5358e44bf9263c71f1cd64c68e888c5233f0fe8ab017e6011277d9527",
    "frame_03_0171_rgb448.npy": "7bf716a4f68defdb85066a0afeed955c61305628a2f43563b0b14ee539644b13",
}
STACK_SHA = "5911485955780036ac4c8990bcaa248667f2e86bd1fd6f9b0783002553b4adff"
RESULTS = PACKAGE / ("preflight" if PREFLIGHT_ONLY else "results") / VARIANT
OMITTED_BOUNDARY_DOCS = {
    "M259_BOUNDARY.md", "M260_BOUNDARY.md", "M261_BOUNDARY.md",
    "M269_BOUNDARY.md", "M273_BOUNDARY.md", "M276_BOUNDARY.md",
    "M277_BOUNDARY.md",
}


def digest(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for part in iter(lambda: stream.read(4 << 20), b""):
            h.update(part)
    return h.hexdigest()


def atomic_json(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_name(path.name + f".partial-{os.getpid()}")
    temp.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    os.replace(temp, path)


def checked_run(args: list[str], env: dict[str, str], label: str) -> None:
    print(f"M328_PHASE_BEGIN {label} monotonic={time.monotonic():.6f}", flush=True)
    completed = subprocess.run(args, env=env, cwd=RELEASE, check=False, timeout=180)
    print(f"M328_PHASE_END {label} rc={completed.returncode} monotonic={time.monotonic():.6f}", flush=True)
    if completed.returncode:
        raise RuntimeError(f"{label} failed rc={completed.returncode}")


def module_paths() -> list[Path]:
    d = RELEASE / "deployment/mage_vl4b"
    paths = [
        RELEASE / "runtime_site",
        d / "m277_m276_fixed_window_board_candidate",
        d / "m254_dual_path_web_candidate",
        d / "m243_web_prefill_board_candidate",
        d / "m242_m241_fixed_text_board_candidate",
        d / "m238_input_prefetch_board_candidate",
        d / "m241_grouped_gqa_board_candidate",
        d / "m231_parse_reuse_board_candidate",
        RELEASE / "tmp/m227_runtime_base/m227_runtime_base_patch",
        RELEASE / "tmp/m223_realtime/m223_realtime_delta",
        RELEASE / "tmp/m218_dual_source/m218_dual_source_delta",
        d / "m181_m120_video_board_candidate/text_runtime",
        d / "m181_m120_video_board_candidate/ps_vision_payload",
        d / "m181_m120_video_board_candidate",
        d / "m175_m120_fixed_text_candidate/runtime",
        d / "m175_m120_fixed_text_candidate/runtime/support",
    ]
    if VARIANT == "candidate":
        paths.insert(0, PACKAGE)
    return paths


def verify_m277_release_subset(candidate: Path) -> dict:
    manifest_path = candidate / "PACKAGE_MANIFEST.json"
    if digest(manifest_path) != M277_SHA:
        raise RuntimeError("M277 frozen manifest hash mismatch")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if (manifest.get("schema") != "tellme-m277-m276-fixed-window-v1" or
            manifest.get("status") != "PASS_OFFLINE_READY_FOR_M277_BOARD_GATE" or
            manifest.get("file_count") != len(manifest.get("files", []))):
        raise RuntimeError("M277 frozen manifest schema/count mismatch")
    expected = {item["path"]: item for item in manifest["files"]}
    actual = {path.relative_to(candidate).as_posix() for path in candidate.rglob("*")
              if path.is_file() and path.name != "PACKAGE_MANIFEST.json"}
    if set(expected) - actual != OMITTED_BOUNDARY_DOCS or actual - set(expected):
        raise RuntimeError(f"M277 release subset mismatch omitted={sorted(set(expected)-actual)} extra={sorted(actual-set(expected))}")
    for name in sorted(actual):
        item = expected[name]
        path = candidate / name
        if path.stat().st_size != item["bytes"] or digest(path) != item["sha256"]:
            raise RuntimeError(f"M277 runtime payload hash mismatch: {name}")
        if path.suffix == ".py":
            ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    return {"manifest_sha256": M277_SHA, "verified_present_files": len(actual),
            "omitted_nonruntime_docs": sorted(OMITTED_BOUNDARY_DOCS)}


def main() -> int:
    record: dict = {
        "gate": "M332-isolated-fixed-video-parser-scale-AB",
        "status": "FAIL",
        "variant": VARIANT,
        "release_root": str(RELEASE),
        "addon_root": str(ADDON),
        "build_id_expected": "0x4D395832",
        "entry": "M277 M276ShortPromptBinaryRuntime.stream (direct 4B inference)",
        "fast_alarm_gate_used": False,
        "semantic_inference_executed": False,
        "stable_service_modified": False,
        "boot_dtb_cma_partitions_changed": False,
    }
    started = time.monotonic()
    try:
        if VARIANT not in ("baseline", "candidate"):
            raise RuntimeError("M332_VARIANT must be baseline or candidate")
        if digest(M332_SOURCE) != M332_SOURCE_SHA:
            raise RuntimeError("M332 candidate parser source hash mismatch")
        if digest(ADDON / "PACKAGE_MANIFEST.json") != "4eb8c6c95752208b5848e0e52efb2a713f98487f5b88518dbd5b58801d236568":
            raise RuntimeError("M328 frozen video companion hash mismatch")
        if not hasattr(os, "geteuid") or os.geteuid() != 0:
            raise RuntimeError("root is required")
        if subprocess.run(["sudo", "-n", "true"], check=False).returncode != 0:
            raise RuntimeError("same-terminal sudo -n true failed")
        if digest(RELEASE / "INSTALL_PACKAGE_MANIFEST.json") != MANIFEST_SHA:
            raise RuntimeError("v7 installed manifest identity mismatch")
        if not (RELEASE / "RUNTIME_SITE_READY.json").is_file() and not (RELEASE / "runtime_site/RUNTIME_SITE_READY.json").is_file():
            raise RuntimeError("isolated runtime installation marker missing")
        RESULTS.mkdir(parents=True, exist_ok=True)
        with socket.socket() as sock:
            try:
                sock.bind(("127.0.0.1", 8001))
            except OSError as exc:
                raise RuntimeError("port 8001 occupied; refusing concurrent FPGA service") from exc

        dirs = module_paths()
        if not all(path.is_dir() and (
            path.resolve().is_relative_to(RELEASE) or
            (VARIANT == "candidate" and path.resolve() == PACKAGE.resolve())
        ) for path in dirs):
            raise RuntimeError("release-only module closure missing or escaped")
        env = os.environ.copy()
        env.update({
            "XILINX_XRT": "/usr", "TMPDIR": "/dev/shm",
            "PYTHONDONTWRITEBYTECODE": "1", "TRANSFORMERS_OFFLINE": "1", "HF_HUB_OFFLINE": "1",
            "PYTHONPATH": os.pathsep.join(map(str, dirs)),
            "PATH": "/usr/local/share/pynq-venv/bin:/usr/local/bin:/usr/bin:/bin",
        })
        py = "/usr/local/share/pynq-venv/bin/python3"
        preflight_spec = importlib.util.spec_from_file_location("release_preflight", RELEASE / "scripts/preflight.py")
        if preflight_spec is None or preflight_spec.loader is None:
            raise RuntimeError("release preflight import unavailable")
        preflight = importlib.util.module_from_spec(preflight_spec)
        preflight_spec.loader.exec_module(preflight)
        config = json.loads((RELEASE / "configs/deployment.example.json").read_text(encoding="utf-8"))
        inspected = preflight.inspect(config, port_check=True)
        record["release_preflight"] = {key: inspected[key] for key in ("status", "build_id", "missing", "hash_or_identity_mismatch", "port_free")}
        if inspected["status"] != "READY_FOR_BOARD_PREFLIGHT":
            raise RuntimeError("release asset preflight blocked")
        d = RELEASE / "deployment/mage_vl4b"
        text = d / "m175_m120_fixed_text_candidate"
        video = d / "m181_m120_video_board_candidate"
        candidate = d / "m277_m276_fixed_window_board_candidate"
        env_gate_result = RESULTS / "environment.json"
        checked_run([
            py, str(text / "runtime/m120_board_env_preflight.py"),
            "--candidate", str(text),
            "--expected-package-manifest-sha256", "406dcca340e4604baeb761445795391c43ec26bd99fa06ffae893d597b17414f",
            "--result", str(env_gate_result),
        ], env, "board-environment")
        record["m277_release_subset"] = verify_m277_release_subset(candidate)
        print("M328_M277_RELEASE_SUBSET_HASH_PASS", flush=True)
        sys.path[:0] = [str(path) for path in dirs]
        import m276_m254_video_server  # noqa: F401
        import m222_video_server
        import video_server
        import m236_prefill_runtime
        parser_source = Path(m236_prefill_runtime.__file__).resolve()
        parser_hash = digest(parser_source)
        record["m236_module_path"] = str(parser_source)
        record["m236_module_sha256"] = parser_hash
        if VARIANT == "candidate":
            if parser_source != M332_SOURCE.resolve() or parser_hash != M332_SOURCE_SHA:
                raise RuntimeError("candidate M236 parser was not imported")
        elif parser_hash != STABLE_M236_SHA or not parser_source.is_relative_to(RELEASE):
            raise RuntimeError("stable M236 parser was not imported")
        if (m222_video_server.M222PSVisionRuntime.__name__ != "M273LatestPSVisionRuntime" or
                video_server.M120VideoRuntime.__name__ != "M276ShortPromptBinaryRuntime"):
            raise RuntimeError("M277 runtime import identity mismatch")
        print("M328_M277_IMPORT_CLOSURE_PASS", flush=True)
        if PREFLIGHT_ONLY:
            record["status"] = "PASS_PREOVERLAY_CLOSURE"
            return 0

        import numpy as np
        names = list(FRAMES)
        for name in names:
            if digest(ADDON / "fixtures" / name) != FRAMES[name]:
                raise RuntimeError(f"fixture hash mismatch: {name}")
        frames = np.stack([np.load(ADDON / "fixtures" / name, allow_pickle=False) for name in names])
        if frames.shape != (4, 448, 448, 3) or frames.dtype != np.uint8:
            raise RuntimeError(f"fixture shape/dtype mismatch: {frames.shape}/{frames.dtype}")
        if hashlib.sha256(frames.tobytes()).hexdigest() != STACK_SHA:
            raise RuntimeError("ordered four-frame tensor hash mismatch")
        record["submitted_frame_count"] = 4
        record["submitted_frame_names"] = names
        record["submitted_frame_file_sha256"] = FRAMES
        record["submitted_tensor_sha256"] = STACK_SHA
        print(f"M328_FRAMES_ACCEPTED count=4 ordered_tensor_sha256={STACK_SHA}", flush=True)

        m277_result = RESULTS / "m277_fixed_video.json"
        cmd = [
            py, str(candidate / "m277_fixed_window_gate.py"),
            "--candidate", str(video), "--text-candidate", str(text),
            "--weights-root", str(RELEASE / "external_assets/weights"),
            "--board-gate", str(RELEASE / "tmp/m223_realtime/m223_realtime_delta/M223_PREDECESSOR_SUMMARY.json"),
            "--fixture-root", str(ADDON / "fixtures"),
            "--m244-baseline", str(candidate / "M244_M243_FIXED_FOUR_FRAME_BOARD_RESULT_02.json"),
            "--package-manifest-sha256", M277_SHA, "--result", str(m277_result),
        ]
        print(f"M328_PHASE_BEGIN video-forward monotonic={time.monotonic():.6f}", flush=True)
        record["semantic_path_invoked"] = True
        timed_out = [False]
        with (RESULTS / "video_forward.log").open("w", encoding="utf-8") as output:
            proc = subprocess.Popen(cmd, cwd=RELEASE, env=env, stdout=subprocess.PIPE,
                                    stderr=subprocess.STDOUT, text=True, bufsize=1,
                                    start_new_session=True)

            def expire() -> None:
                if proc.poll() is None:
                    timed_out[0] = True
                    os.killpg(proc.pid, signal.SIGTERM)

            timer = threading.Timer(900.0, expire)
            timer.start()
            try:
                assert proc.stdout is not None
                for line in proc.stdout:
                    output.write(line)
                    output.flush()
                    print(line, end="", flush=True)
                rc = proc.wait(timeout=30)
            finally:
                timer.cancel()
                if proc.poll() is None:
                    os.killpg(proc.pid, signal.SIGTERM)
                    proc.wait(timeout=30)
        print(f"M328_PHASE_END video-forward rc={rc} monotonic={time.monotonic():.6f}", flush=True)
        if timed_out[0]:
            raise TimeoutError("fixed video forward exceeded 900 seconds")
        if not m277_result.is_file():
            raise RuntimeError(f"M277 video result missing; process rc={rc}")
        result = json.loads(m277_result.read_text(encoding="utf-8"))
        record["m277_result_sha256"] = digest(m277_result)
        record["m277_status"] = result.get("status")
        record["first_exception"] = result.get("error")
        record["stage_timing_ms"] = result.get("stage_timing_ms")
        record["stage_events"] = [item.get("payload") for item in result.get("events", []) if item.get("event") == "stage"]
        record["selected_frame_indices"] = result.get("selected_frame_indices")
        record["prompt_tokens"] = result.get("prompt_tokens")
        record["first_token_ms"] = result.get("first_token_ms")
        record["final_output"] = [item.get("payload") for item in result.get("events", []) if item.get("event") in ("token", "knife_observation", "complete")]
        proof = next((item.get("payload", {}).get("proof", {}) for item in result.get("events", []) if item.get("event") == "complete"), {})
        record["fpga_proof"] = proof
        record["vision_stage_reached"] = any(item.get("name") == "vision" for item in record["stage_events"] if isinstance(item, dict))
        record["prefill_stage_reached"] = any(item.get("name") == "prefill" for item in record["stage_events"] if isinstance(item, dict))
        record["semantic_inference_executed"] = bool(record["prefill_stage_reached"] and proof.get("pl_logical_chain_calls", 0) > 0)
        record["semantic_inference_completed"] = result.get("functional_status") == "PASS"
        if (rc != 0 or result.get("functional_status") != "PASS" or
                result.get("frames_sha256") != STACK_SHA or
                str(proof.get("build_id", "")).lower() != "0x4d395832" or
                proof.get("pl_logical_chain_calls") != 778 or
                proof.get("language_cpu_linear_fallback") is not False):
            raise RuntimeError(f"fixed video E2E gate failed: rc={rc} error={result.get('error')}")
        record["status"] = "PASS_INDEPENDENT_VIDEO_E2E"
    except BaseException as exc:
        if not record.get("first_exception"):
            record["first_exception"] = f"{type(exc).__name__}: {exc}"
    finally:
        record["elapsed_ms"] = (time.monotonic() - started) * 1000.0
        atomic_json(RESULTS / "result.json", record)
        print(json.dumps(record, ensure_ascii=False), flush=True)
        print("M328_RELEASE_VIDEO_GATE_PASS" if record["status"].startswith("PASS") else "M328_RELEASE_VIDEO_GATE_FAIL", flush=True)
    return 0 if record["status"].startswith("PASS") else 1


if __name__ == "__main__":
    raise SystemExit(main())
