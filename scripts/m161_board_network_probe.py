#!/usr/bin/env python3
"""Read-only KV260 Ethernet inventory for the temporary M120 transfer path."""

from __future__ import annotations

import json
import subprocess
from pathlib import Path


def read(path: Path, default: str = "") -> str:
    try:
        return path.read_text(encoding="utf-8").strip()
    except OSError:
        return default


def ip_json(*arguments: str) -> list[dict]:
    completed = subprocess.run(
        ["ip", "-j", *arguments], check=True, text=True,
        stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
    )
    value = json.loads(completed.stdout)
    if not isinstance(value, list):
        raise RuntimeError("unexpected ip JSON root")
    return value


def main() -> int:
    interfaces = []
    for root in sorted(Path("/sys/class/net").iterdir()):
        name = root.name
        if name == "lo":
            continue
        carrier = read(root / "carrier", "unknown")
        interfaces.append(
            {
                "name": name,
                "operstate": read(root / "operstate", "unknown"),
                "carrier": carrier,
                "speed_mbps": read(root / "speed", "unknown"),
                "address": read(root / "address", "unknown"),
                "is_ethernet_candidate": (root / "device").exists(),
            }
        )
    addresses = ip_json("-4", "addr", "show")
    routes = ip_json("-4", "route", "show")
    linked = [item["name"] for item in interfaces if item["carrier"] == "1"]
    result = {
        "date": "2026-09-01",
        "gate": "M161-KV260-temporary-network-readonly-probe",
        "status": "PASS" if linked else "FAIL",
        "classification": "Read-only interface/link/address/route inventory; no address, route, service, boot, DTB, CMA or partition change.",
        "interfaces": interfaces,
        "linked_interfaces": linked,
        "ipv4_addresses": addresses,
        "ipv4_routes": routes,
        "state_changed": False,
    }
    print("__M161_NETWORK_PROBE_RESULT_BEGIN__", flush=True)
    print(json.dumps(result, separators=(",", ":")), flush=True)
    print("__M161_NETWORK_PROBE_RESULT_END__", flush=True)
    print("M161_KV260_NETWORK_PROBE_PASS" if result["status"] == "PASS" else "M161_KV260_NETWORK_PROBE_FAIL", flush=True)
    return 0 if result["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
