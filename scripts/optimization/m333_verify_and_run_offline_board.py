#!/usr/bin/env python3
"""Verify and run one isolated M333 CPU-only package on KV260, never load PL."""

import argparse
import hashlib
import io
import json
import os
from pathlib import Path
import subprocess
import tarfile
import tempfile

BASE = Path("/home/ubuntu")
TARGET = BASE / "m333_offline_board_01"
ARCHIVE = BASE / "m333_offline_board_01.tar.gz"
CONTRACT = BASE / "m333_offline_board_01_contract.json"
PYTHON = "/usr/local/share/pynq-venv/bin/python"


def sha(data):
    return hashlib.sha256(data).hexdigest()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--contract-sha256", required=True)
    args = parser.parse_args()
    if os.geteuid() == 0:
        raise RuntimeError("CPU-only M333 test must not run as root")
    if TARGET.exists():
        raise FileExistsError("immutable M333 board target already exists")
    contract_raw = CONTRACT.read_bytes()
    if sha(contract_raw) != args.contract_sha256:
        raise RuntimeError("M333 transfer contract SHA mismatch")
    contract = json.loads(contract_raw)
    archive_raw = ARCHIVE.read_bytes()
    if len(archive_raw) != contract["archive_bytes"] or sha(archive_raw) != contract["archive_sha256"]:
        raise RuntimeError("M333 archive size or SHA mismatch")
    rows = {row["path"]: row for row in contract["files"]}
    if len(rows) != 6 or len(rows) != len(contract["files"]):
        raise RuntimeError("M333 package file count mismatch")
    with tempfile.TemporaryDirectory(prefix="m333-verify-", dir=BASE) as temp_name:
        staging = Path(temp_name) / "payload"
        staging.mkdir()
        with tarfile.open(fileobj=io.BytesIO(archive_raw), mode="r:gz") as handle:
            members = handle.getmembers()
            if {item.name for item in members} != set(rows) or len(members) != len(rows):
                raise RuntimeError("M333 tar path whitelist mismatch")
            for item in members:
                if not item.isfile() or item.issym() or item.islnk():
                    raise RuntimeError("M333 tar non-file member")
                target = (staging / item.name).resolve()
                target.relative_to(staging.resolve())
                raw = handle.extractfile(item).read()
                row = rows[item.name]
                if len(raw) != row["bytes"] or sha(raw) != row["sha256"]:
                    raise RuntimeError("M333 member identity mismatch: " + item.name)
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_bytes(raw)
        staging.rename(TARGET)
    environment = dict(os.environ, PYTHONDONTWRITEBYTECODE="1")
    candidate = TARGET / "deployment/m333"
    results = []
    for name, script in (("scheduler", "test_m333_review_bridge.py"),
                         ("http_sse", "test_m333_http_sse.py")):
        output = TARGET / (name + "_result.json")
        completed = subprocess.run([PYTHON, str(candidate / script), "--output", str(output)],
                                   cwd=TARGET, env=environment, capture_output=True,
                                   text=True, timeout=30)
        result = json.loads(output.read_text()) if output.is_file() else None
        results.append({"name": name, "returncode": completed.returncode,
                        "result": result, "stdout": completed.stdout[-4000:],
                        "stderr": completed.stderr[-4000:]})
        if completed.returncode or result is None or result.get("status") != "PASS":
            break
    value = {"gate": "M333-KV260-CPU-only-fake-runtime", "status":
             "PASS" if len(results) == 2 and all(x["returncode"] == 0 for x in results) else "FAIL",
             "archive_sha256": contract["archive_sha256"],
             "contract_sha256": args.contract_sha256,
             "overlay_loaded": False, "stable_service_modified": False,
             "tests": results}
    path = TARGET / "BOARD_RESULT.json"
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print("M333_BOARD_RESULT_BEGIN")
    print(json.dumps(value, ensure_ascii=False))
    print("M333_BOARD_RESULT_END")
    return 0 if value["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
