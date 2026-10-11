#!/usr/bin/env python3
"""Read-only KV260 memory/service identity gate for the M269 candidate."""

from __future__ import annotations

import argparse
import hashlib
import json
import platform
import sys
import urllib.request
from pathlib import Path


sys.dont_write_bytecode = True
EXPECTED_BUILD = "0x4d395832"
EXPECTED_MODE = "M254-dual-path-latest-only"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def meminfo() -> dict[str, int]:
    wanted = {
        "MemTotal", "MemAvailable", "Cached", "SReclaimable",
        "SwapTotal", "SwapFree", "CmaTotal", "CmaFree",
    }
    result: dict[str, int] = {}
    for line in Path("/proc/meminfo").read_text(encoding="utf-8").splitlines():
        key, value = line.split(":", 1)
        if key in wanted:
            result[key] = int(value.strip().split()[0])
    missing = sorted(wanted - result.keys())
    if missing:
        raise RuntimeError(f"missing meminfo keys: {missing}")
    return result


def nested_values(value, key: str):
    if isinstance(value, dict):
        for name, child in value.items():
            if name == key:
                yield child
            yield from nested_values(child, key)
    elif isinstance(value, list):
        for child in value:
            yield from nested_values(child, key)


def service_processes() -> list[dict]:
    found = []
    needles = ("m254_video_server", "m243_video_server", "mage_m120")
    for entry in Path("/proc").iterdir():
        if not entry.name.isdigit():
            continue
        try:
            command = (entry / "cmdline").read_bytes().replace(b"\0", b" ").decode("utf-8", "replace").strip()
            if not command or not any(needle in command for needle in needles):
                continue
            status = {}
            for line in (entry / "status").read_text(encoding="utf-8").splitlines():
                if line.startswith(("VmRSS:", "VmHWM:", "VmSize:")):
                    name, rest = line.split(":", 1)
                    status[name] = int(rest.strip().split()[0])
            found.append({"pid": int(entry.name), "command": command[:512], **status})
        except (FileNotFoundError, PermissionError, ProcessLookupError):
            continue
    return sorted(found, key=lambda item: item["pid"])


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--expected-self-sha256", required=True)
    parser.add_argument("--cache-bytes", type=int, required=True)
    parser.add_argument("--reserve-mib", type=int, required=True)
    args = parser.parse_args()
    observed_self = sha256(Path(__file__).resolve())
    if observed_self != args.expected_self_sha256:
        raise RuntimeError(f"self hash mismatch {observed_self}")
    if platform.machine() != "aarch64":
        raise RuntimeError(f"unexpected architecture {platform.machine()}")

    with urllib.request.urlopen("http://127.0.0.1:8001/api/health", timeout=5) as response:
        health = json.loads(response.read().decode("utf-8"))
    builds = {str(value).lower() for value in nested_values(health, "build_id")}
    modes = {str(value) for value in nested_values(health, "mode")}
    statuses = {str(value) for value in nested_values(health, "status")}
    memory = meminfo()
    reserve_bytes = args.reserve_mib * 1024 * 1024
    available_bytes = memory["MemAvailable"] * 1024
    required_bytes = args.cache_bytes + reserve_bytes
    identity_pass = EXPECTED_BUILD in builds and EXPECTED_MODE in modes and "running" in statuses
    headroom_pass = available_bytes >= required_bytes
    processes = service_processes()
    process_rss_kib = sum(item.get("VmRSS", 0) for item in processes)
    result = {
        "date": "2026-09-02",
        "gate": "M270-M269-KV260-read-only-memory-headroom",
        "status": "PASS_READ_ONLY_HEADROOM" if identity_pass and headroom_pass else "FAIL_READ_ONLY_HEADROOM",
        "classification": "Read-only active-service identity and Linux memory headroom; no candidate upload, model execution, overlay load, Web replacement or TTFT measurement.",
        "architecture": platform.machine(),
        "active_service": {
            "build_ids": sorted(builds),
            "modes": sorted(modes),
            "statuses": sorted(statuses),
            "identity_pass": identity_pass,
        },
        "memory_kib": memory,
        "m269_cache_bytes": args.cache_bytes,
        "fixed_post_cache_reserve_mib": args.reserve_mib,
        "required_available_bytes": required_bytes,
        "observed_available_bytes": available_bytes,
        "projected_available_after_cache_bytes": available_bytes - args.cache_bytes,
        "headroom_pass": headroom_pass,
        "matching_service_processes": processes,
        "matching_service_rss_kib": process_rss_kib,
        "board_state_changed": False,
        "candidate_uploaded": False,
        "candidate_executed": False,
        "overlay_loaded_or_replaced": False,
        "boot_dtb_cma_partitions_services_changed": False,
        "stable_rollback_preserved": True,
        "next_gate": "Upload the hash-locked M269 delta through COM3 and run one isolated fixed-window identity, constrained 0/1 and complete TTFT gate.",
    }
    print("__M270_MEMORY_RESULT_BEGIN__")
    print(json.dumps(result, separators=(",", ":")))
    print("__M270_MEMORY_RESULT_END__")
    print("M270_BOARD_MEMORY_HEADROOM_PASS" if result["status"].startswith("PASS") else "M270_BOARD_MEMORY_HEADROOM_FAIL")
    return 0 if result["status"].startswith("PASS") else 1


if __name__ == "__main__":
    raise SystemExit(main())
