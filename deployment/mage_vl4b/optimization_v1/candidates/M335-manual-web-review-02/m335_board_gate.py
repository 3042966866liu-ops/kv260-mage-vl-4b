#!/usr/bin/env python3
"""One bounded, isolated KV260 Web→Mage-VL 4B/FPGA→SSE gate.

Uses the already-verified M328 RGB448 video fixture twice as a local loop.
Never changes the stable M254 installation or automatic alarm policy.
"""

from __future__ import annotations

import hashlib
from http.client import HTTPConnection
import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import threading
import time

import numpy as np

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
RELEASE = Path("/home/ubuntu/tellme_release_install_20260926")
ADDON = Path("/home/ubuntu/tellme_release_video_addon_20260926_v3")
PORT = 8013
BUILD_ID = "0x4D395832"
FRAME_NAMES = (
    "frame_00_0068_rgb448.npy", "frame_01_0102_rgb448.npy",
    "frame_02_0137_rgb448.npy", "frame_03_0171_rgb448.npy",
)
FRAME_SHA = (
    "efbd192266329db17ab9b233b854fa4086a16ccf8faf8aace75462c164844e8f",
    "e334ea6bdeb142a42a443afe27fa8af551895d568149ab8aca92a181fdc69243",
    "81ddb1f5358e44bf9263c71f1cd64c68e888c5233f0fe8ab017e6011277d9527",
    "7bf716a4f68defdb85066a0afeed955c61305628a2f43563b0b14ee539644b13",
)


def digest(path: Path) -> str:
    value = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(4 << 20), b""):
            value.update(block)
    return value.hexdigest()


def atomic_json(path: Path, value: dict) -> None:
    temporary = path.with_name(path.name + f".partial-{os.getpid()}")
    temporary.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    os.replace(temporary, path)


def http(method: str, path: str, body: bytes | None = None, media: str | None = None,
         timeout: float = 30.0) -> tuple[int, dict | str]:
    conn = HTTPConnection("127.0.0.1", PORT, timeout=timeout)
    headers = {} if media is None else {"Content-Type": media}
    try:
        conn.request(method, path, body=body, headers=headers)
        response = conn.getresponse()
        raw = response.read()
        content = json.loads(raw) if "application/json" in response.getheader("Content-Type", "") else raw.decode()
        return response.status, content
    finally:
        conn.close()


def wait_for(predicate, seconds: float, label: str, process: subprocess.Popen) -> None:
    deadline = time.monotonic() + seconds
    while time.monotonic() < deadline:
        if process.poll() is not None:
            raise RuntimeError(f"{label}: server exited rc={process.returncode}")
        if predicate():
            return
        time.sleep(1.0)
    raise TimeoutError(f"{label}: timed out after {seconds:.0f}s")


def device_holders() -> list[int]:
    devices = {"/dev/dri/renderD128", "/dev/dri/card1"}
    found = set()
    for entry in Path("/proc").iterdir():
        if not entry.name.isdigit() or int(entry.name) == os.getpid():
            continue
        try:
            for fd in (entry / "fd").iterdir():
                try:
                    if os.readlink(fd) in devices:
                        found.add(int(entry.name))
                except OSError:
                    continue
        except (OSError, PermissionError):
            continue
    return sorted(found)


def module_dirs() -> list[Path]:
    d = RELEASE / "deployment/mage_vl4b"
    return [HERE, RELEASE / "runtime_site", d / "m277_m276_fixed_window_board_candidate",
            d / "m254_dual_path_web_candidate",
            d / "m243_web_prefill_board_candidate", d / "m242_m241_fixed_text_board_candidate",
            d / "m238_input_prefetch_board_candidate", d / "m241_grouped_gqa_board_candidate",
            d / "m231_parse_reuse_board_candidate",
            RELEASE / "tmp/m227_runtime_base/m227_runtime_base_patch",
            RELEASE / "tmp/m223_realtime/m223_realtime_delta",
            RELEASE / "tmp/m218_dual_source/m218_dual_source_delta",
            d / "m181_m120_video_board_candidate/text_runtime",
            d / "m181_m120_video_board_candidate/ps_vision_payload",
            d / "m181_m120_video_board_candidate",
            d / "m175_m120_fixed_text_candidate/runtime",
            d / "m175_m120_fixed_text_candidate/runtime/support"]


def sse_reader(stop: threading.Event, events: list[dict], faults: list[str]) -> None:
    connection = HTTPConnection("127.0.0.1", PORT, timeout=90)
    try:
        connection.request("GET", "/api/4b/video/live/events?after=0")
        response = connection.getresponse()
        if response.status != 200:
            raise RuntimeError(f"SSE returned HTTP {response.status}")
        name = None
        payload = None
        while not stop.is_set():
            raw = response.fp.readline()
            if not raw:
                raise RuntimeError("SSE connection closed")
            line = raw.decode("utf-8").rstrip("\r\n")
            if line.startswith("event: "):
                name = line[7:]
            elif line.startswith("data: "):
                payload = json.loads(line[6:])
            elif line == "" and name is not None:
                events.append({"name": name, "payload": payload})
                name = payload = None
    except BaseException as error:
        if not stop.is_set():
            faults.append(f"{type(error).__name__}: {error}")
    finally:
        connection.close()


def main() -> int:
    result = {"gate": "M335-real-Web-manual-4B-FPGA-SSE", "status": "FAIL",
              "candidate_not_promoted": True, "stable_directory_modified": False,
              "automatic_alarm_threshold_modified": False, "build_id_expected": BUILD_ID,
              "first_error": None, "checks": {}, "events": [], "tasks": []}
    process = None
    service_log = HERE / "service.log"
    stop_sse = threading.Event()
    sse_events: list[dict] = []
    sse_faults: list[str] = []
    sse_thread = None
    started = time.monotonic()
    try:
        if os.geteuid() != 0:
            raise RuntimeError("root required")
        if device_holders():
            raise RuntimeError(f"FPGA device already owned by PIDs {device_holders()}")
        frame_paths = [ADDON / "fixtures" / name for name in FRAME_NAMES]
        if any(not path.is_file() or digest(path) != expected
               for path, expected in zip(frame_paths, FRAME_SHA)):
            raise RuntimeError("M328 real video fixture identity mismatch")
        frames = [np.load(path, allow_pickle=False) for path in frame_paths]
        if any(frame.shape != (448, 448, 3) or frame.dtype != np.uint8 for frame in frames):
            raise RuntimeError("M328 frame shape/dtype mismatch")
        env = os.environ.copy()
        env.update({"PYTHONPATH": os.pathsep.join(map(str, module_dirs())),
                    "PYTHONDONTWRITEBYTECODE": "1", "TRANSFORMERS_OFFLINE": "1", "HF_HUB_OFFLINE": "1"})
        d = RELEASE / "deployment/mage_vl4b"
        env["M254_M243_RESULT"] = str(d / "m254_dual_path_web_candidate/M243_WEB_PREFILL_BOARD_RESULT_05.json")
        env["M254_M253_RESULT"] = str(d / "m254_dual_path_web_candidate/M253_KV260_LATEST_FAST_STREAM_BOARD_RESULT_02.json")
        env["M254_M249_RESULT"] = str(d / "m254_dual_path_web_candidate/M249_KV260_SSDLITE_BOARD_RESULT_03.json")
        env["M254_M249_CANDIDATE"] = str(d / "m249_ssdlite_board_candidate")
        args = [sys.executable, str(HERE / "m335_video_server.py"), "--candidate",
                str(d / "m181_m120_video_board_candidate"), "--text-candidate",
                str(d / "m175_m120_fixed_text_candidate"), "--weights-root",
                str(RELEASE / "external_assets/weights"), "--board-gate",
                str(RELEASE / "tmp/m223_realtime/m223_realtime_delta/M223_PREDECESSOR_SUMMARY.json"),
                "--host", "127.0.0.1", "--port", str(PORT)]
        with service_log.open("wb") as log:
            process = subprocess.Popen(args, env=env, cwd=RELEASE, stdout=log, stderr=subprocess.STDOUT,
                                       start_new_session=True)
            result["service_pid"] = process.pid
            print(f"M335_SERVICE_PID {process.pid}", flush=True)

            def health() -> bool:
                try:
                    status, _ = http("GET", "/api/health", timeout=2)
                    return status == 200
                except (OSError, TimeoutError):
                    return False

            wait_for(health, 180, "listener", process)
            status, html = http("GET", "/index.html")
            result["checks"]["manual_button_visible"] = status == 200 and "手动请求 4B 语义复核" in html
            prompt = "[TELLME_KNIFE_BINARY_V1] Inspect the four video frames. Output exactly one character: 1 if any knife is visible, otherwise 0. Answer:"
            status, body = http("POST", "/api/4b/video/live/start", json.dumps({
                "prompt": prompt, "max_new_tokens": 1, "source_mode": "uploaded-file-loop",
                "source_label": "M328-fixed-video-RGB448-local-loop"}).encode(), "application/json", timeout=240)
            if status != 202:
                raise RuntimeError(f"start rejected HTTP {status}: {body}")
            print("M335_LIVE_START_ACCEPTED", flush=True)

            def runtime_ready() -> bool:
                try:
                    code, value = http("GET", "/api/4b/video/live/status", timeout=4)
                    return code == 200 and value.get("manual_review_available") is True
                except (OSError, TimeoutError):
                    return False

            wait_for(runtime_ready, 600, "4B/FPGA runtime ready", process)
            code, ready = http("GET", "/api/4b/video/live/status")
            result["checks"]["candidate_modules_isolated"] = (
                ready["candidate_module_path"] == str(HERE / "m335_video_server.py")
                and ready["m254_module_path"].startswith(str(RELEASE)))
            result["checks"]["runtime_loaded_once"] = ready["runtime_load_count"] == 1
            result["checks"]["m276_runtime_selected"] = (
                ready.get("semantic_runtime_class") == "M276ShortPromptBinaryRuntime")
            code, missing = http("POST", "/api/4b/video/live/review")
            result["checks"]["missing_frames_explicit"] = code == 409 and missing.get("code") == "MISSING_FRAMES"
            sse_thread = threading.Thread(target=sse_reader, args=(stop_sse, sse_events, sse_faults), daemon=True)
            sse_thread.start()

            def submit_cycle() -> list[int]:
                accepted = []
                for frame in frames:
                    code, value = http("POST", "/api/4b/video/live/frame", frame.tobytes(),
                                       "application/x-tellme-rgb448", timeout=30)
                    if code != 202:
                        raise RuntimeError(f"video frame rejected HTTP {code}: {value}")
                    accepted.append(value["sequence"])
                return accepted

            source_first = submit_cycle()
            code, first = http("POST", "/api/4b/video/live/review")
            if code != 202 or first.get("state") != "active":
                raise RuntimeError(f"first manual request rejected HTTP {code}: {first}")
            result["tasks"].append(first)
            print(f"M335_TASK1_ACCEPTED task={first['task_id']} source={source_first}", flush=True)
            wait_for(lambda: any(e["name"] == "window_begin" and e["payload"].get("sequences") == [0, 1, 2, 3]
                                 for e in sse_events), 60, "first 4B window begin", process)
            source_second = submit_cycle()
            code, second = http("POST", "/api/4b/video/live/review")
            if code != 202 or second.get("state") != "waiting":
                raise RuntimeError(f"busy manual request rejected HTTP {code}: {second}")
            result["tasks"].append(second)
            result["checks"]["busy_latest_window"] = (
                source_first == [0, 1, 2, 3] and source_second == [4, 5, 6, 7]
                and first["source_sequences"] == source_first
                and second["source_sequences"] == source_second
                and first["task_id"] != second["task_id"])
            print(f"M335_TASK2_WAITING task={second['task_id']} source={source_second}", flush=True)
            wait_for(lambda: len([e for e in sse_events if e["name"] == "semantic_review_released"
                                  and e["payload"].get("trigger") == "manual"]) >= 2,
                     900, "two real manual review completions", process)
            code, final = http("GET", "/api/4b/video/live/status")
            results = [e["payload"] for e in sse_events if e["name"] == "semantic_review_result"
                       and e["payload"].get("trigger") == "manual"]
            releases = [e["payload"] for e in sse_events if e["name"] == "semantic_review_released"
                        and e["payload"].get("trigger") == "manual"]
            result["events"] = [{"name": e["name"], "payload": e["payload"]} for e in sse_events
                                if e["name"] in ("semantic_review_queued", "semantic_review_waiting",
                                                  "semantic_review_result", "semantic_review_released",
                                                  "window_begin", "window_complete", "window_error")]
            result["checks"]["two_task_results_bound"] = (
                [item["task_id"] for item in results] == [first["task_id"], second["task_id"]]
                and [item["task_id"] for item in releases] == [first["task_id"], second["task_id"]]
                and all(item["terminal_event"] == "window_complete" for item in releases))
            result["checks"]["real_fpga_proof_both"] = all(
                item["complete"].get("proof", {}).get("result") == "PASS"
                and item["complete"]["proof"].get("build_id", "").lower() == BUILD_ID.lower()
                and item["complete"]["proof"].get("pl_logical_chain_calls") == 778
                and item["complete"].get("prompt_tokens") == 159
                and item["complete"]["proof"].get("language_cpu_linear_fallback") is False
                for item in results) and len(results) == 2
            result["checks"]["no_fake_auto_alarm"] = not any(
                e["name"] == "safety_result" and e["payload"].get("alarm", {}).get("active")
                for e in sse_events)
            result["checks"]["recovered_for_next_event"] = (
                final["semantic_review"]["active_task_id"] is None
                and final["semantic_review"]["waiting_task_id"] is None
                and final["manual_review_available"]
                and final["runtime_load_count"] == 1
                and final["semantic_terminal_monitor_error"] is None)
            result["checks"]["sse_healthy"] = not sse_faults
            result["final_status"] = final
            result["sse_event_count"] = len(sse_events)
            result["status"] = "PASS_MANUAL_WEB_ONLY" if all(result["checks"].values()) else "FAIL"
    except BaseException as error:
        result["first_error"] = f"{type(error).__name__}: {error}"
        print(f"M335_FIRST_ERROR {result['first_error']}", flush=True)
    finally:
        stop_sse.set()
        if process is not None:
            try:
                os.killpg(process.pid, signal.SIGTERM)
                process.wait(timeout=30)
            except (ProcessLookupError, subprocess.TimeoutExpired):
                result["service_stop_error"] = "service did not stop cleanly"
            result["service_exit_code"] = process.poll()
        result["elapsed_s"] = time.monotonic() - started
        result["service_log"] = str(service_log)
        result["service_log_sha256"] = digest(service_log) if service_log.is_file() else None
        result["sse_faults"] = sse_faults
        atomic_json(HERE / "BOARD_RESULT.json", result)
        print("M335_BOARD_RESULT " + json.dumps({"status": result["status"], "checks": result["checks"],
                                                "first_error": result["first_error"],
                                                "service_log_sha256": result["service_log_sha256"]}), flush=True)
    return 0 if result["status"] == "PASS_MANUAL_WEB_ONLY" else 1


if __name__ == "__main__":
    raise SystemExit(main())
