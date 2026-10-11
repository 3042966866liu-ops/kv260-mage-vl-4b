#!/usr/bin/env python3
"""Serve the exact M120 payload over one whitelist-only direct Ethernet endpoint."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import unquote, urlsplit


ROOT = Path(__file__).resolve().parents[1]
AUDIT = ROOT / "deployment/mage_vl4b/M141_M120_FULLTEXT_USB_SOURCE_AUDIT_RESULT.json"
M140 = ROOT / "deployment/mage_vl4b/M140_M120_SINGLE_CHAIN_BOARD_RESULT_01.json"
EXPECTED_M140_SHA = "60bc5dad7f3609c32b4698ebbb372eba9a3ab9e74b273969dd322299b4431cbb"
EXPECTED_LANGUAGE = "12ea4b8cc58639d0aab6da4ef3a3f12bbbb1254f88865f76512a5f0d00d4ae5d"
EXPECTED_HEAD = "a1a555700e3daec8049627564c73e5783affe3827ab5437665249786d5c079ef"
EXPECTED_PAYLOAD_BYTES = 2_035_472_384
PREFIX = "/tellme_m120_fulltext_0x4D395832"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(32 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def wsl_unc(linux_path: str) -> Path:
    if not linux_path.startswith("/") or ".." in Path(linux_path).parts:
        raise RuntimeError(f"unsafe WSL source path: {linux_path}")
    return Path("\\\\wsl.localhost\\Ubuntu-24.04\\" + linux_path.lstrip("/").replace("/", "\\"))


def build_files() -> tuple[dict[str, Path], dict]:
    if sha256(M140) != EXPECTED_M140_SHA:
        raise RuntimeError("M162 exact M140 identity mismatch")
    m140 = json.loads(M140.read_text(encoding="utf-8"))
    if m140.get("status") != "PASS" or m140.get("gate") != "M140-M120-COM3-single-chain":
        raise RuntimeError("M162 requires real M140 PASS")
    audit = json.loads(AUDIT.read_text(encoding="utf-8"))
    if audit.get("status") != "PASS" or int(audit.get("payload_bytes", -1)) != EXPECTED_PAYLOAD_BYTES:
        raise RuntimeError("M162 M141 audit mismatch")
    if audit["language"]["manifest_sha256"] != EXPECTED_LANGUAGE or audit["lm_head"]["manifest_sha256"] != EXPECTED_HEAD:
        raise RuntimeError("M162 layout identity mismatch")
    sources: dict[str, Path] = {}
    entries: list[dict] = []
    for key, target in (("language", "language_fourport"), ("lm_head", "lmhead_fourport")):
        section = audit[key]
        source_root = wsl_unc(section["root"])
        manifest = source_root / "SIXPORT_LAYOUT_MANIFEST.json"
        relative = f"{target}/SIXPORT_LAYOUT_MANIFEST.json"
        sources[relative] = manifest
        entries.append({"path": relative, "bytes": manifest.stat().st_size, "sha256": section["manifest_sha256"], "payload": False})
        for item in section["files"]:
            relative = f"{target}/{item['path']}"
            sources[relative] = source_root / item["path"]
            entries.append({"path": relative, "bytes": int(item["bytes"]), "sha256": item["sha256"], "payload": True})
    if len(entries) != 10:
        raise RuntimeError("M162 expected ten payload members")
    for entry in entries:
        source = sources[entry["path"]]
        if not source.is_file() or source.stat().st_size != entry["bytes"] or sha256(source) != entry["sha256"]:
            raise RuntimeError(f"M162 source drift: {entry['path']}")
    manifest = {
        "date": "2026-09-01",
        "gate": "M162-M120-direct-Ethernet-payload",
        "status": "PASS",
        "candidate_build_id": "0x4D395832",
        "m140_result_sha256": EXPECTED_M140_SHA,
        "m141_audit_sha256": sha256(AUDIT),
        "language_manifest_sha256": EXPECTED_LANGUAGE,
        "lm_head_manifest_sha256": EXPECTED_HEAD,
        "payload_bytes": EXPECTED_PAYLOAD_BYTES,
        "file_count": len(entries),
        "files": entries,
    }
    return sources, manifest


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--bind", default="192.168.0.10")
    parser.add_argument("--port", type=int, default=8765)
    args = parser.parse_args()
    sources, manifest = build_files()
    manifest_bytes = (json.dumps(manifest, indent=2) + "\n").encode()
    manifest_sha = hashlib.sha256(manifest_bytes).hexdigest()
    ready_bytes = (json.dumps({
        "status": "READY",
        "candidate_build_id": "0x4D395832",
        "network_payload_manifest_sha256": manifest_sha,
        "file_count": 10,
        "payload_bytes": EXPECTED_PAYLOAD_BYTES,
    }, indent=2) + "\n").encode()
    memory = {
        "NETWORK_PAYLOAD_MANIFEST.json": manifest_bytes,
        "NETWORK_READY.json": ready_bytes,
    }

    class Handler(BaseHTTPRequestHandler):
        server_version = "TeLLMe-M162/1"

        def log_message(self, format: str, *values: object) -> None:
            print("M162_HTTP", self.address_string(), format % values, flush=True)

        def do_HEAD(self) -> None:
            self._serve(False)

        def do_GET(self) -> None:
            self._serve(True)

        def _serve(self, body: bool) -> None:
            request = unquote(urlsplit(self.path).path)
            if not request.startswith(PREFIX + "/"):
                self.send_error(404)
                return
            relative = request[len(PREFIX) + 1:]
            if relative in memory:
                payload = memory[relative]
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(payload)))
                self.end_headers()
                if body:
                    self.wfile.write(payload)
                return
            source = sources.get(relative)
            if source is None:
                self.send_error(404)
                return
            size = source.stat().st_size
            self.send_response(200)
            self.send_header("Content-Type", "application/octet-stream")
            self.send_header("Content-Length", str(size))
            self.end_headers()
            if body:
                with source.open("rb") as stream:
                    for block in iter(lambda: stream.read(4 << 20), b""):
                        self.wfile.write(block)

    server = ThreadingHTTPServer((args.bind, args.port), Handler)
    print(json.dumps({
        "gate": "M162-M120-readonly-HTTP-publisher",
        "status": "READY",
        "bind": args.bind,
        "port": args.port,
        "url": f"http://{args.bind}:{args.port}{PREFIX}",
        "network_payload_manifest_sha256": manifest_sha,
        "payload_bytes": EXPECTED_PAYLOAD_BYTES,
        "file_count": 10,
        "source_rehash_pass": True,
    }, indent=2), flush=True)
    print("M162_M120_READONLY_HTTP_READY", flush=True)
    try:
        server.serve_forever(poll_interval=0.2)
    finally:
        server.server_close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
