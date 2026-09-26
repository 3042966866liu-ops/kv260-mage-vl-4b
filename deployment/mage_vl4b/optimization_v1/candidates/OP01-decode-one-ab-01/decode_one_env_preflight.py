#!/usr/bin/env python3
"""One fixed environment and package-identity preflight before M120 overlay load."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import subprocess
import tempfile
from pathlib import Path


EXPECTED_XCLBINUTIL = Path("/usr/local/share/pynq-venv/bin/xclbinutil")


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(16 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--candidate", type=Path, required=True)
    parser.add_argument("--expected-package-manifest-sha256", required=True)
    parser.add_argument("--result", type=Path, required=True)
    args = parser.parse_args()
    result: dict[str, object] = {"gate": "OP01-decode-one-board-environment", "status": "FAIL"}
    try:
        if os.geteuid() != 0:
            raise RuntimeError("root preflight required")
        if os.environ.get("XILINX_XRT") != "/usr":
            raise RuntimeError("XILINX_XRT must be /usr")
        if Path(tempfile.gettempdir()).resolve() != Path("/dev/shm"):
            raise RuntimeError("TMPDIR must resolve to /dev/shm")
        selected = shutil.which("xclbinutil")
        if selected is None or Path(selected).resolve() != EXPECTED_XCLBINUTIL.resolve():
            raise RuntimeError(f"wrong xclbinutil selected: {selected}")
        version = subprocess.run(
            [selected, "--version"], check=True, text=True,
            stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
        ).stdout.splitlines()
        manifest_path = args.candidate / "PACKAGE_MANIFEST.json"
        observed_manifest = sha256(manifest_path)
        if observed_manifest != args.expected_package_manifest_sha256:
            raise RuntimeError("candidate package manifest hash mismatch")
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        expected_paths = {item["path"] for item in manifest["files"]}
        observed_paths = {
            path.relative_to(args.candidate).as_posix()
            for path in args.candidate.rglob("*")
            if path.is_file() and path.name != "PACKAGE_MANIFEST.json"
            and "__pycache__" not in path.parts and path.suffix != ".pyc"
        }
        if observed_paths != expected_paths:
            raise RuntimeError("package path whitelist mismatch")
        for item in manifest["files"]:
            path = args.candidate / item["path"]
            if path.stat().st_size != int(item["bytes"]) or sha256(path) != item["sha256"]:
                raise RuntimeError(f"package file identity mismatch: {item['path']}")
        for relative in ("overlay/op01_decode_one.bit", "overlay/op01_decode_one.hwh"):
            if relative not in expected_paths:
                raise RuntimeError(f"overlay artifact absent from whitelist: {relative}")
        from pynq._3rdparty import xrt
        from pynq.pl_server import Device

        probe_count = int(xrt.xclProbe()) if xrt.XRT_SUPPORTED else 0
        device_count = len(Device.devices)
        if not xrt.XRT_SUPPORTED or probe_count != 1 or device_count != 1:
            raise RuntimeError(
                f"XRT/PYNQ device gate failed: supported={xrt.XRT_SUPPORTED} "
                f"probe={probe_count} devices={device_count}"
            )
        result = {
            "gate": "OP01-decode-one-board-environment",
            "status": "PASS",
            "euid": os.geteuid(),
            "xilinx_xrt": os.environ["XILINX_XRT"],
            "tmpdir": str(Path(tempfile.gettempdir()).resolve()),
            "xclbinutil": str(Path(selected).resolve()),
            "xclbinutil_version_first_line": version[0] if version else "",
            "xrt_supported": bool(xrt.XRT_SUPPORTED),
            "xcl_probe_count": probe_count,
            "pynq_device_count": device_count,
            "package_manifest_sha256": observed_manifest,
            "verified_file_count": len(observed_paths),
        }
    except Exception as exc:
        result["error"] = f"{type(exc).__name__}: {exc}"
    args.result.parent.mkdir(parents=True, exist_ok=True)
    args.result.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, indent=2), flush=True)
    print("OP01_DECODE_ONE_BOARD_ENV_PASS" if result["status"] == "PASS" else "OP01_DECODE_ONE_BOARD_ENV_FAIL")
    return 0 if result["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())

