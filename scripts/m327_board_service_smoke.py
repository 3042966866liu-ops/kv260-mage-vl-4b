#!/usr/bin/env python3
"""Bounded, isolated first-install service smoke; never serves external clients."""

import hashlib
import importlib.util
import json
import os
from pathlib import Path
import signal
import socket
import subprocess
import sys
import time
import urllib.error
import urllib.request


ROOT = Path("/home/ubuntu/tellme_release_install_20260926")
RESULT = ROOT / "results/m327_first_install_service"
EXPECTED_MANIFEST = "fc69e69c0396e29e06d4852b06f680b2365cb31fdd1ffb036b0f85037b6f6d6e"
URL = "http://127.0.0.1:8001"


def request(path, payload=None, timeout=10):
    data = None if payload is None else json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        URL + path,
        data=data,
        headers={} if data is None else {"Content-Type": "application/json"},
        method="GET" if data is None else "POST",
    )
    with urllib.request.urlopen(req, timeout=timeout) as response:
        return response.status, json.load(response)


def wait_status(proc, deadline, expected, label):
    last = None
    next_heartbeat = time.monotonic() + 30
    while time.monotonic() < deadline:
        if proc.poll() is not None:
            raise RuntimeError(f"release service exited rc={proc.returncode}")
        if time.monotonic() >= next_heartbeat:
            raw = (Path("/proc") / str(proc.pid) / "cmdline").read_bytes()
            command = raw.split(b"\0")[0].decode("utf-8", errors="replace")
            print(f"M327_SERVICE_WAIT phase={label} pid={proc.pid} command={command} status={last}", flush=True)
            next_heartbeat = time.monotonic() + 30
        try:
            code, value = request("/api/4b/video/live/status")
            last = value
            if code == 200 and expected(value):
                return value
            if value.get("worker_error") or value.get("service_state") == "worker-failed":
                raise RuntimeError(f"release worker failed: {value.get('worker_error')}")
        except (urllib.error.URLError, TimeoutError, ConnectionError):
            pass
        time.sleep(2)
    raise TimeoutError(f"release status timed out: {last}")


def main():
    if os.geteuid() != 0 or subprocess.run(["sudo", "-n", "true"], check=False).returncode != 0:
        raise RuntimeError("same-terminal root/sudo required")
    manifest = ROOT / "INSTALL_PACKAGE_MANIFEST.json"
    if hashlib.sha256(manifest.read_bytes()).hexdigest() != EXPECTED_MANIFEST:
        raise RuntimeError("install manifest identity mismatch")
    with socket.socket() as sock:
        try:
            sock.bind(("127.0.0.1", 8001))
        except OSError as exc:
            raise RuntimeError("port 8001 is occupied; refusing concurrent FPGA service") from exc
    RESULT.mkdir(parents=True, exist_ok=True)
    log_path = RESULT / "service.log"
    record = {
        "gate": "M327-isolated-release-service-smoke",
        "status": "FAIL",
        "install_root": str(ROOT),
        "build_id_expected": "0x4D395832",
        "video_inference_run": False,
        "stable_service_modified": False,
    }
    proc = None
    try:
        env = os.environ.copy()
        env["TELLME_RELEASE_BOARD_LAUNCH_UNVERIFIED"] = "ACKNOWLEDGED"
        env["PYTHONDONTWRITEBYTECODE"] = "1"
        with log_path.open("w", encoding="utf-8") as out:
            proc = subprocess.Popen(
                ["bash", str(ROOT / "scripts/run_demo.sh")],
                cwd=ROOT,
                env=env,
                stdout=out,
                stderr=subprocess.STDOUT,
                start_new_session=True,
            )
        idle = wait_status(proc, time.monotonic() + 300, lambda v: v.get("status") == "idle", "idle")
        if str(idle.get("build_id", "")).lower() != "0x4d395832":
            raise RuntimeError("service health Build-ID mismatch")
        record["idle_status"] = {k: idle.get(k) for k in ("status", "build_id", "kernel")}
        code, started = request("/api/4b/video/live/start", {
            "prompt": "请描述画面。", "max_new_tokens": 1,
            "source_mode": "browser-camera", "source_label": "m327-no-frames-smoke",
        }, timeout=180)
        if code != 202:
            raise RuntimeError(f"session start HTTP {code}: {started}")
        ready = wait_status(
            proc, time.monotonic() + 240,
            lambda v: v.get("status") == "running"
            and v.get("board_runtime_loaded") is True
            and v.get("runtime_load_count") == 1
            and v.get("worker_alive") is True,
            "runtime-ready",
        )
        if str(ready.get("build_id", "")).lower() != "0x4d395832":
            raise RuntimeError("ready Build-ID mismatch")
        if ready.get("web_board_runtime_class") != "M238PrefillRuntime":
            raise RuntimeError(f"unexpected board runtime class: {ready.get('web_board_runtime_class')}")
        raw_cmd = (Path("/proc") / str(proc.pid) / "cmdline").read_bytes()
        cmdline = [part.decode("utf-8") for part in raw_cmd.split(b"\0") if part]
        raw_env = (Path("/proc") / str(proc.pid) / "environ").read_bytes()
        entries = dict(part.decode("utf-8", errors="replace").split("=", 1)
                       for part in raw_env.split(b"\0") if b"=" in part)
        py_paths = entries.get("PYTHONPATH", "").split(os.pathsep)
        if not py_paths or not all(Path(path).is_relative_to(ROOT) for path in py_paths if path):
            raise RuntimeError("service PYTHONPATH escaped release root")
        if not any("/m254_dual_path_web_candidate/m254_video_server.py" in part for part in cmdline):
            raise RuntimeError("service entry is not release M254")
        sys.path[:0] = py_paths
        origins = {}
        for name in ("m243_video_server", "video_server", "m238_prefill_runtime", "m241_video_language_runtime", "fast_frame_pipeline"):
            spec = importlib.util.find_spec(name)
            if spec is None or spec.origin is None or not Path(spec.origin).is_relative_to(ROOT):
                raise RuntimeError(f"module resolution escaped release root: {name}")
            origins[name] = spec.origin
        record.update({
            "status": "PASS_RUNTIME_READY_NO_VIDEO_INFERENCE",
            "ready_status": {k: ready.get(k) for k in (
                "status", "service_state", "build_id", "kernel", "board_runtime_loaded",
                "runtime_load_count", "worker_alive", "web_board_runtime_class",
                "web_language_model_class", "web_language_runtime", "t64_used")},
            "service_pid": proc.pid,
            "service_cmdline": cmdline,
            "service_pythonpath": py_paths,
            "module_resolution": origins,
        })
    except Exception as exc:
        record["error"] = f"{type(exc).__name__}: {exc}"
    finally:
        if proc is not None and proc.poll() is None:
            os.killpg(proc.pid, signal.SIGTERM)
            try:
                proc.wait(timeout=25)
            except subprocess.TimeoutExpired:
                os.killpg(proc.pid, signal.SIGKILL)
                proc.wait(timeout=10)
        record["service_stopped"] = proc is None or proc.poll() is not None
        if log_path.exists() and record["status"] != "PASS_RUNTIME_READY_NO_VIDEO_INFERENCE":
            record["log_tail"] = log_path.read_text(encoding="utf-8", errors="replace").splitlines()[-25:]
        tmp = RESULT / "result.json.tmp"
        tmp.write_text(json.dumps(record, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        os.replace(tmp, RESULT / "result.json")
        print(json.dumps(record, ensure_ascii=False), flush=True)
        print("M327_RELEASE_SERVICE_SMOKE_PASS" if record["status"] == "PASS_RUNTIME_READY_NO_VIDEO_INFERENCE" else "M327_RELEASE_SERVICE_SMOKE_FAIL", flush=True)
    return 0 if record["status"] == "PASS_RUNTIME_READY_NO_VIDEO_INFERENCE" else 1


if __name__ == "__main__":
    raise SystemExit(main())
