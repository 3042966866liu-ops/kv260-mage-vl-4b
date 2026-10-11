#!/usr/bin/env python3
"""Exercise both fail-closed and PASS branches of the M294 UART collector."""

from __future__ import annotations

import json
from pathlib import Path
import subprocess
import sys
import tempfile


PACKAGE_HASH = "a" * 64


def run_collector(log: Path, result: Path) -> subprocess.CompletedProcess[str]:
    collector = Path(__file__).with_name("m294_collect_counterbalanced_uart.py")
    return subprocess.run(
        [
            sys.executable,
            "-B",
            str(collector),
            "--log",
            str(log),
            "--result",
            str(result),
            "--package-manifest-sha256",
            PACKAGE_HASH,
        ],
        check=False,
        text=True,
        capture_output=True,
    )


def main() -> int:
    with tempfile.TemporaryDirectory(prefix="tellme-m294-collector-") as temp_name:
        temp = Path(temp_name)
        incomplete_log = temp / "incomplete.log"
        incomplete_result = temp / "incomplete.json"
        incomplete_log.write_text(
            "M294_MEASUREMENT_00_PASS tokens=127 calls=624/624 prefill_ms=1.250\n",
            encoding="utf-8",
        )
        failed = run_collector(incomplete_log, incomplete_result)
        failed_json = json.loads(incomplete_result.read_text(encoding="utf-8"))
        if failed.returncode != 1 or failed_json.get("status") != "FAIL_INCOMPLETE_UART_EVIDENCE":
            raise RuntimeError("M294 collector fail-closed branch did not execute")
        if failed_json.get("completed_measurement_markers") != 1:
            raise RuntimeError("M294 collector partial marker count mismatch")

        passed_log = temp / "passed.log"
        passed_result = temp / "passed.json"
        envelope = {
            "gate": "M294-real-KV260-counterbalanced-T32-boundary-pilot",
            "status": "PASS_COUNTERBALANCED_PILOT",
            "package_manifest_sha256": PACKAGE_HASH,
            "plan_sha256": "424dd30c09e57ce6982a3e2bb08835641dabc38e63bc66d33284a57f6eb07162",
            "completed_measurements": 27,
            "records": [{"measurement_index": index} for index in range(27)],
        }
        passed_log.write_text(
            "__M294_BOARD_RESULT_BEGIN__\n"
            + json.dumps(envelope, separators=(",", ":"))
            + "\n__M294_BOARD_RESULT_END__\n"
            + "__M294_GATE_RC_0__\n__M294_RESTORE_RC_0__\n",
            encoding="utf-8",
        )
        passed = run_collector(passed_log, passed_result)
        passed_json = json.loads(passed_result.read_text(encoding="utf-8"))
        if passed.returncode != 0 or passed_json.get("host_collection", {}).get("status") != "PASS":
            raise RuntimeError("M294 collector PASS branch did not execute")
    print("M294_COLLECTOR_CONTRACT_PASS fail_closed=true pass_branch=true")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
