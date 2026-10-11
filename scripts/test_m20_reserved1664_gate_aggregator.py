#!/usr/bin/env python3
"""Exercise the embedded M20 final-evidence aggregator without hardware."""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
GATE = ROOT / "deployment/qwen25_3b_directddr_chain/run_reserved1664_m20_full_gate.sh"


def extract_aggregator() -> str:
    source = GATE.read_text()
    blocks = source.split("<<'PY'\n")
    if len(blocks) != 3:
        raise RuntimeError(f"expected two embedded Python blocks, got {len(blocks) - 1}")
    return blocks[2].split("\nPY\n", 1)[0]


def run_case(directory: Path, *, omit_decode: bool) -> tuple[int, dict]:
    directory.mkdir(parents=True)
    script = directory / "aggregator.py"
    script.write_text(extract_aggregator())
    matched = directory / "matched.json"
    artifact = directory / "artifact.json"
    board_identity = directory / "board_identity.json"
    boot = directory / "boot.json"
    cma_reclaim = directory / "cma_reclaim.json"
    memory = directory / "memory.json"
    mapping = directory / "mapping.log"
    prefill = directory / "prefill.log"
    decode = directory / "decode.log"
    e2e = directory / "e2e.log"
    result = directory / "result.json"
    matched.write_text(json.dumps({"gate": "qwen25-3b-matched-cpu-fpga-comparison-identity", "status": "PASS"}) + "\n")
    artifact.write_text(json.dumps({"gate": "m20-resident-sequential-prefill-executable-artifact-preflight", "status": "PASS"}) + "\n")
    board_identity.write_text(json.dumps({"gate": "qwen25-3b-live-board-model-identity-preflight", "status": "PASS"}) + "\n")
    boot.write_text(json.dumps({"gate": "plain-reserved1664-boot-preflight", "status": "PASS"}) + "\n")
    cma_reclaim.write_text(
        json.dumps({"gate": "reserved1664-post-identity-cma-reclaim", "status": "PASS"}) + "\n"
    )
    memory.write_text(json.dumps({"gate": "qwen25-3b-resident-cma-preflight", "status": "PASS"}) + "\n")
    mapping.write_text(json.dumps({"gate": "reserved1664-driver-mapping-smoke", "status": "PASS"}) + "\n")
    prefill.write_text(json.dumps({"gate": "highddr-prefill-real-weight-address-smoke", "status": "PASS"}) + "\n")
    decode.write_text(
        "" if omit_decode else json.dumps({"gate": "directddr-chain-two-descriptor-smoke", "status": "PASS"}) + "\n"
    )
    e2e.write_text(json.dumps({"gate": "qwen25-3b-resident-sequential-prefill-full-e2e-cpu-gate", "status": "PASS"}) + "\n")
    completed = subprocess.run(
        [
            sys.executable,
            str(script),
            str(matched),
            str(artifact),
            str(board_identity),
            str(boot),
            str(cma_reclaim),
            str(memory),
            str(mapping),
            str(prefill),
            str(decode),
            str(e2e),
            str(result),
            "0",
        ],
        check=False,
    )
    return completed.returncode, json.loads(result.read_text())


def main() -> int:
    with tempfile.TemporaryDirectory(prefix="tellme-reserved1664-") as raw:
        directory = Path(raw)
        pass_rc, passed = run_case(directory / "pass", omit_decode=False)
        fail_rc, failed = run_case(directory / "fail", omit_decode=True)
    assert pass_rc == 0 and passed["status"] == "PASS"
    assert passed["milestone"] == "M20"
    assert passed["gate"] == "plain-reserved1664-full-board-gate"
    assert all(
        key in passed
        for key in (
            "boot_preflight",
            "post_identity_cma_reclaim",
            "memory_preflight",
            "mapping_smoke",
            "prefill_smoke",
            "decode_smoke",
            "full_e2e_cpu_gate",
            "matched_cpu_fpga_identity",
            "artifact_preflight",
            "live_board_model_identity",
        )
    )
    assert fail_rc == 1 and failed["status"] == "FAIL"
    assert failed["decode_smoke"]["reason"] == "expected-one-record-got-0"
    print("QWEN_M20_RESERVED1664_AGGREGATOR_UNIT_PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
