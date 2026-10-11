#!/usr/bin/env python3
"""Receive, install and smoke-test the isolated M189 ARM64 runtime."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import socket
import struct
import subprocess
import time
from pathlib import Path


MAGIC = b"TELLME_M190_V1\n"
BUNDLE_SHA = "88c3fefaae94a475751bef3348e0048f30fc90bb1f27caa20e79f2e0f77361ba"
EXPECTED_FILES = 37
EXPECTED_WHEELS = 35
PYTHON = Path("/usr/local/share/pynq-venv/bin/python")
ROOT = Path("/home/ubuntu/tellme_m120_m89x2_20260901")


def sha256(path: Path) -> str:
    value = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(32 << 20), b""):
            value.update(block)
    return value.hexdigest()


def atomic_json(path: Path, value: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + f".partial-{os.getpid()}")
    temporary.write_text(json.dumps(value, indent=2) + "\n", encoding="utf-8")
    os.replace(temporary, path)


def receive_exact(stream: socket.socket, count: int) -> bytes:
    value = bytearray(count)
    view = memoryview(value)
    offset = 0
    while offset < count:
        observed = stream.recv_into(view[offset:], count - offset)
        if observed == 0:
            raise RuntimeError(f"unexpected EOF at {offset}/{count}")
        offset += observed
    return bytes(value)


def send_json(stream: socket.socket, value: dict) -> None:
    payload = (json.dumps(value, separators=(",", ":")) + "\n").encode()
    stream.sendall(struct.pack("!I", len(payload)) + payload)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--bind", default="192.168.0.2")
    parser.add_argument("--port", type=int, default=8768)
    parser.add_argument("--result", type=Path, required=True)
    args = parser.parse_args()
    started = time.monotonic()
    result = {
        "date": "2026-09-01",
        "gate": "M190-M189-KV260-isolated-ARM64-Mage-VL-runtime-install",
        "status": "FAIL",
        "classification": "Board runtime dependency installation/smoke only; not PS vision or FPGA video E2E evidence.",
        "bundle_manifest_sha256": BUNDLE_SHA,
        "boot_dtb_cma_partitions_services_changed": False,
        "stable_rollback_preserved": True,
    }
    connection = None
    bundle_partial = ROOT / "m189_arm64_mage_runtime_bundle.push-partial"
    bundle = ROOT / "m189_arm64_mage_runtime_bundle"
    install_partial = ROOT / "m190_mage_runtime.partial"
    install = ROOT / "m190_mage_runtime"
    try:
        if os.geteuid() != 0 or not PYTHON.is_file():
            raise RuntimeError("M190 requires root and the fixed PYNQ Python")
        if any(path.exists() for path in (bundle_partial, bundle, install_partial, install)):
            raise RuntimeError("M190 requires absent bundle/install destinations")
        free_before = shutil.disk_usage(ROOT).free
        if free_before < 1300 << 20:
            raise RuntimeError(f"M190 insufficient free bytes before transfer: {free_before}")
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as listener:
            listener.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            listener.bind((args.bind, args.port))
            listener.listen(1)
            listener.settimeout(180)
            print(f"M190_BOARD_RECEIVER_READY bind={args.bind} port={args.port}", flush=True)
            connection, peer = listener.accept()
        connection.settimeout(3600)
        if peer[0] != "192.168.0.10" or receive_exact(connection, len(MAGIC)) != MAGIC:
            raise RuntimeError("M190 peer/protocol identity mismatch")
        manifest_size = struct.unpack("!I", receive_exact(connection, 4))[0]
        if not 0 < manifest_size <= 2 << 20:
            raise RuntimeError("M190 unsafe manifest size")
        transport = json.loads(receive_exact(connection, manifest_size))
        if transport.get("gate") != "M190-M189-ARM64-runtime-direct-Ethernet-payload" or transport.get("status") != "PASS":
            raise RuntimeError("M190 transport manifest identity mismatch")
        if transport.get("bundle_manifest_sha256") != BUNDLE_SHA or transport.get("file_count") != EXPECTED_FILES:
            raise RuntimeError("M190 transport closure mismatch")
        entries = {item["path"]: item for item in transport["files"]}
        if len(entries) != EXPECTED_FILES or sum(int(x["bytes"]) for x in entries.values()) != transport.get("total_bytes"):
            raise RuntimeError("M190 transport count/bytes mismatch")
        bundle_partial.mkdir()
        copied = []
        for ordinal in range(EXPECTED_FILES):
            name_size = struct.unpack("!H", receive_exact(connection, 2))[0]
            name = receive_exact(connection, name_size).decode()
            size = struct.unpack("!Q", receive_exact(connection, 8))[0]
            item = entries.get(name)
            if item is None or int(item["bytes"]) != size or Path(name).name != name:
                raise RuntimeError(f"M190 unsafe member identity: {name}")
            target = bundle_partial / name
            value = hashlib.sha256()
            with target.open("xb") as output:
                remaining = size
                while remaining:
                    block = connection.recv(min(4 << 20, remaining))
                    if not block:
                        raise RuntimeError(f"M190 EOF in {name}")
                    output.write(block)
                    value.update(block)
                    remaining -= len(block)
                output.flush()
                os.fsync(output.fileno())
            if value.hexdigest() != item["sha256"] or sha256(target) != item["sha256"]:
                raise RuntimeError(f"M190 member hash mismatch: {name}")
            copied.append(name)
            print(f"M190_RECEIVE_MEMBER_PASS ordinal={ordinal+1}/{EXPECTED_FILES} path={name}", flush=True)
        if receive_exact(connection, 2) != b"\x00\x00" or set(copied) != set(entries):
            raise RuntimeError("M190 received closure mismatch")
        if sha256(bundle_partial / "BUNDLE_MANIFEST.json") != BUNDLE_SHA:
            raise RuntimeError("M190 bundle manifest mismatch")
        bundle_json = json.loads((bundle_partial / "BUNDLE_MANIFEST.json").read_text())
        if bundle_json.get("file_count") != EXPECTED_WHEELS:
            raise RuntimeError("M190 wheel count mismatch")
        for item in bundle_json["files"]:
            path = bundle_partial / item["path"]
            if not path.is_file() or path.stat().st_size != item["bytes"] or sha256(path) != item["sha256"]:
                raise RuntimeError(f"M190 locked wheel mismatch: {item['path']}")
        os.replace(bundle_partial, bundle)
        bundle_partial = None

        install_partial.mkdir()
        wheels = [str(bundle / item["path"]) for item in bundle_json["files"]]
        command = [str(PYTHON), "-m", "pip", "install", "--no-index", "--no-deps", "--no-cache-dir", "--no-compile", "--target", str(install_partial)] + wheels
        completed = subprocess.run(command, text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=1800)
        result["pip_output_tail"] = completed.stdout[-12000:]
        if completed.returncode != 0:
            raise RuntimeError(f"M190 isolated pip install failed rc={completed.returncode}")

        candidate = ROOT / "m181_m120_video_board_candidate"
        smoke = r'''
import importlib, json, os, platform, sys, types, torch
import numpy, transformers, safetensors, tokenizers, huggingface_hub, pynq
assert platform.machine().lower() in {"aarch64", "arm64"}
assert torch.__version__ == "2.12.1+cpu"
assert transformers.__version__ == "5.7.0"
assert numpy.__version__ == "1.26.4"
torch.set_num_threads(4)
x = torch.arange(32, dtype=torch.float32).reshape(4, 8) / 32
w = torch.arange(64, dtype=torch.float32).reshape(8, 8) / 64
y32 = torch.nn.functional.linear(x, w)
ybf = torch.nn.functional.linear(x.to(torch.bfloat16), w.to(torch.bfloat16)).float()
assert torch.isfinite(y32).all() and torch.isfinite(ybf).all()
root = os.environ["M190_CANDIDATE"]
payload = os.path.join(root, "ps_vision_payload")
name = "m190_mage_payload"
package = types.ModuleType(name); package.__path__ = [payload]; sys.modules[name] = package
importlib.import_module(name + ".configuration_mage_vl")
importlib.import_module(name + ".modeling_mage_vl")
print(json.dumps({"architecture": platform.machine(), "python": sys.version.split()[0], "torch": torch.__version__, "transformers": transformers.__version__, "numpy": numpy.__version__, "safetensors": safetensors.__version__, "tokenizers": tokenizers.__version__, "huggingface_hub": huggingface_hub.__version__, "pynq": getattr(pynq, "__version__", "present"), "bf16_max_abs_vs_fp32": float((y32-ybf).abs().max()), "mage_source_import": True}))
'''
        environment = os.environ.copy()
        environment["PYTHONPATH"] = str(install_partial)
        environment["PYTHONDONTWRITEBYTECODE"] = "1"
        environment["TRANSFORMERS_OFFLINE"] = "1"
        environment["HF_HUB_OFFLINE"] = "1"
        environment["M190_CANDIDATE"] = str(candidate)
        smoke_run = subprocess.run([str(PYTHON), "-c", smoke], env=environment, text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=300)
        result["smoke_output"] = smoke_run.stdout[-12000:]
        if smoke_run.returncode != 0:
            raise RuntimeError(f"M190 runtime smoke failed rc={smoke_run.returncode}")
        smoke_json = json.loads(smoke_run.stdout.strip().splitlines()[-1])
        os.replace(install_partial, install)
        install_partial = None
        result.update({
            "status": "PASS",
            "transport": "direct-Ethernet-PC-outbound-push",
            "peer": peer[0],
            "bundle": str(bundle),
            "isolated_site_packages": str(install),
            "file_count": EXPECTED_FILES,
            "wheel_count": EXPECTED_WHEELS,
            "total_bytes": transport["total_bytes"],
            "free_bytes_before": free_before,
            "free_bytes_after": shutil.disk_usage(ROOT).free,
            "smoke": smoke_json,
            "next_gate": "Rerun only the fixed four-frame M186 PS vision numerical gate with this isolated PYTHONPATH.",
        })
        send_json(connection, {"status": "PASS", "bundle_manifest_sha256": BUNDLE_SHA, "isolated_site_packages": str(install)})
    except BaseException as error:
        result["error"] = f"{type(error).__name__}: {error}"
        result["next_gate"] = "Repair and rerun only M190 runtime installation; do not run PS vision."
        if connection is not None:
            try:
                send_json(connection, {"status": "FAIL", "error": result["error"]})
            except OSError:
                pass
    finally:
        if connection is not None:
            connection.close()
        result["total_ms"] = (time.monotonic() - started) * 1000
        atomic_json(args.result.resolve(), result)
    print("__M190_RUNTIME_INSTALL_RESULT_BEGIN__", flush=True)
    print(json.dumps(result, separators=(",", ":")), flush=True)
    print("__M190_RUNTIME_INSTALL_RESULT_END__", flush=True)
    print("M190_ARM64_MAGE_RUNTIME_INSTALL_PASS" if result["status"] == "PASS" else "M190_ARM64_MAGE_RUNTIME_INSTALL_FAIL", flush=True)
    return 0 if result["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
