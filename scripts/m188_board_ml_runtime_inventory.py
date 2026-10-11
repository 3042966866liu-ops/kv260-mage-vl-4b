#!/usr/bin/env python3
"""One-shot, read-only inventory of usable ARM64 ML runtimes on the KV260."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import platform
import shutil
import subprocess
import sys
import time
from pathlib import Path


sys.dont_write_bytecode = True
RESULT = Path("/home/ubuntu/tellme_m120_m89x2_20260901/results/M188_BOARD_ML_RUNTIME_INVENTORY_RESULT.json")
PACKAGE_MANIFEST = Path("/home/ubuntu/tellme_m120_m89x2_20260901/m181_m120_video_board_candidate/PACKAGE_MANIFEST.json")
PACKAGE_SHA = "1596536bfe6865cb7eab5c038d8b4da8b666afc7cbd629ddc4559781727151d6"
PYTHONS = [
    "/usr/bin/python3",
    "/usr/local/share/pynq-venv/bin/python3",
    "/usr/local/share/pynq-venv/bin/python",
]
MODULES = ["torch", "onnxruntime", "tflite_runtime", "tensorflow", "numpy", "scipy", "cv2", "safetensors", "transformers"]
PROBE = r'''import importlib,importlib.util,json,platform,sys
mods={}
for name in %r:
    found=importlib.util.find_spec(name) is not None
    item={"found":found}
    if found:
        try:
            module=importlib.import_module(name)
            item["imported"]=True
            item["version"]=str(getattr(module,"__version__","unknown"))
            item["path"]=str(getattr(module,"__file__",None))
        except BaseException as error:
            item["imported"]=False
            item["error"]=f"{type(error).__name__}: {error}"
    mods[name]=item
print(json.dumps({"executable":sys.executable,"version":sys.version.split()[0],"machine":platform.machine(),"modules":mods},separators=(",",":")))''' % (MODULES,)


def sha256(path: Path) -> str:
    value = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(4 << 20), b""):
            value.update(block)
    return value.hexdigest()


def atomic_json(path: Path, value: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + f".partial-{os.getpid()}")
    temporary.write_text(json.dumps(value, indent=2) + "\n", encoding="utf-8")
    os.replace(temporary, path)


def command_output(arguments: list[str], timeout: int = 30) -> dict:
    try:
        completed = subprocess.run(arguments, text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=timeout)
        return {"exit_code": completed.returncode, "output": completed.stdout[-12000:]}
    except BaseException as error:
        return {"exit_code": None, "error": f"{type(error).__name__}: {error}"}


def wheels() -> list[dict]:
    found = []
    for root, directories, files in os.walk("/home/ubuntu"):
        directories[:] = [name for name in directories if name not in {"__pycache__", ".cache", ".git"}]
        for name in files:
            if name.endswith(".whl"):
                path = Path(root) / name
                found.append({"path": str(path), "bytes": path.stat().st_size})
                if len(found) >= 200:
                    return found
    return found


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--expected-self-sha256", required=True)
    parser.add_argument("--result", type=Path, required=True)
    args = parser.parse_args()
    if args.result.resolve() != RESULT:
        raise RuntimeError("M188 fixed result path mismatch")
    if sha256(Path(__file__).resolve()) != args.expected_self_sha256:
        raise RuntimeError("M188 self hash mismatch")
    if sha256(PACKAGE_MANIFEST) != PACKAGE_SHA:
        raise RuntimeError("M188 M181 package identity mismatch")
    started = time.monotonic()
    probes = []
    for executable in PYTHONS:
        path = Path(executable)
        if not path.exists():
            probes.append({"requested": executable, "exists": False})
            continue
        raw = command_output([executable, "-c", PROBE])
        entry = {"requested": executable, "exists": True, **raw}
        if raw.get("exit_code") == 0:
            try:
                entry["probe"] = json.loads(raw["output"].strip().splitlines()[-1])
            except BaseException as error:
                entry["parse_error"] = f"{type(error).__name__}: {error}"
        probes.append(entry)
    dpkg = command_output(["/usr/bin/dpkg-query", "-W", "-f=${Package}\t${Version}\n"])
    if dpkg.get("exit_code") == 0:
        needles = ("torch", "onnx", "tensorflow", "numpy", "scipy", "opencv", "openblas", "blas", "eigen")
        dpkg["matching_packages"] = [line for line in dpkg.pop("output").splitlines() if any(name in line.lower() for name in needles)]
    meminfo = {}
    for line in Path("/proc/meminfo").read_text(encoding="utf-8").splitlines():
        key, value = line.split(":", 1)
        if key in {"MemTotal", "MemAvailable", "SwapTotal", "SwapFree"}:
            meminfo[key] = value.strip()
    result = {
        "date": "2026-09-01",
        "gate": "M188-KV260-ARM64-ML-runtime-inventory",
        "status": "PASS_INVENTORY",
        "classification": "Read-only environment inventory after M186 dependency failure; not model execution or deployment evidence.",
        "architecture": platform.machine(),
        "kernel": platform.release(),
        "python_probes": probes,
        "dpkg": dpkg,
        "local_board_wheels": wheels(),
        "memory": meminfo,
        "root_filesystem": {"free_bytes": shutil.disk_usage("/").free, "total_bytes": shutil.disk_usage("/").total},
        "package_manifest_sha256": PACKAGE_SHA,
        "board_state_changed": False,
        "boot_dtb_cma_partitions_services_changed": False,
        "stable_rollback_preserved": True,
        "total_ms": (time.monotonic() - started) * 1000.0,
    }
    atomic_json(args.result, result)
    print("__M188_ML_RUNTIME_INVENTORY_BEGIN__")
    print(json.dumps(result, separators=(",", ":")))
    print("__M188_ML_RUNTIME_INVENTORY_END__")
    print("M188_BOARD_ML_RUNTIME_INVENTORY_PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
