#!/usr/bin/env python3
"""Fault-inject the embedded reserved1664 cleanup evidence finalizer."""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
GATE = ROOT / "deployment/qwen25_3b_directddr_chain/run_reserved1664_full_gate.sh"


def extract_cleanup_finalizer() -> str:
    source = GATE.read_text()
    blocks = source.split("<<'PY'\n")
    if len(blocks) != 3:
        raise RuntimeError(f"expected two embedded Python blocks, got {len(blocks) - 1}")
    return blocks[1].split("\nPY\n", 1)[0]


def run_finalizer(
    directory: Path,
    *,
    original_rc: int,
    cleanup_rc: int,
    stage: str,
    initial_result: dict | str | None = None,
    partials: dict[str, dict] | None = None,
) -> tuple[int, dict]:
    directory.mkdir(parents=True)
    script = directory / "finalizer.py"
    script.write_text(extract_cleanup_finalizer())
    result = directory / "result.json"
    if isinstance(initial_result, dict):
        result.write_text(json.dumps(initial_result) + "\n")
    elif isinstance(initial_result, str):
        result.write_text(initial_result)

    partial_names = ("artifact", "boot", "identity", "cma_reclaim", "memory")
    partial_paths = {name: directory / f"{name}.json" for name in partial_names}
    for name, payload in (partials or {}).items():
        partial_paths[name].write_text(json.dumps(payload) + "\n")

    completed = subprocess.run(
        [
            sys.executable,
            str(script),
            str(result),
            str(original_rc),
            str(cleanup_rc),
            stage,
            *(str(partial_paths[name]) for name in partial_names),
        ],
        check=False,
    )
    return completed.returncode, json.loads(result.read_text())


def main() -> int:
    source = GATE.read_text()
    assert source.index("trap cleanup EXIT") < source.index('"$PYTHON" "$ARTIFACT_PREFLIGHT"')
    with tempfile.TemporaryDirectory(prefix="tellme-cleanup-finalizer-") as raw:
        root = Path(raw)
        rc, early = run_finalizer(
            root / "early",
            original_rc=1,
            cleanup_rc=0,
            stage="boot_preflight",
            partials={
                "artifact": {"gate": "reserved1664-executable-artifact-preflight", "status": "PASS"},
                "boot": {"gate": "plain-reserved1664-boot-preflight", "status": "FAIL"},
            },
        )
        assert rc == 0
        assert early["status"] == "FAIL"
        assert early["reason"] == "gate-exited-before-final-result"
        assert early["failed_stage"] == "boot_preflight"
        assert early["artifact_preflight"]["status"] == "PASS"
        assert early["boot_preflight"]["status"] == "FAIL"
        assert early["cleanup"]["status"] == "PASS"

        rc, process_failed = run_finalizer(
            root / "process-failed",
            original_rc=17,
            cleanup_rc=0,
            stage="final_evidence_aggregation",
            initial_result={"gate": "plain-reserved1664-full-board-gate", "status": "PASS"},
        )
        assert rc == 0
        assert process_failed["status"] == "FAIL"
        assert process_failed["cleanup"]["original_process_rc"] == 17

        rc, cleanup_failed = run_finalizer(
            root / "cleanup-failed",
            original_rc=0,
            cleanup_rc=91,
            stage="final_evidence_aggregation",
            initial_result={"gate": "plain-reserved1664-full-board-gate", "status": "PASS"},
        )
        assert rc == 0
        assert cleanup_failed["status"] == "FAIL"
        assert cleanup_failed["cleanup"]["status"] == "FAIL"
        assert cleanup_failed["cleanup"]["cleanup_rc"] == 91

        rc, unreadable = run_finalizer(
            root / "unreadable",
            original_rc=1,
            cleanup_rc=0,
            stage="decode_smoke",
            initial_result="{not-json",
        )
        assert rc == 0
        assert unreadable["status"] == "FAIL"
        assert unreadable["reason"].startswith("unreadable-precleanup-result:")

    print("QWEN_RESERVED1664_CLEANUP_FINALIZER_UNIT_PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
