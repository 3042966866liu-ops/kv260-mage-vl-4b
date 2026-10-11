#!/usr/bin/env python3
"""Fail-closed verifier for the isolated M233 T64 RTL timeout gate."""

from __future__ import annotations

import hashlib
import json
import os
import re
import sys
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SIM = ROOT / "tmp" / "m233_t64_timeout_expected_failure" / "sim" / "verilog"
LOG = SIM / "xsim.log"
TB = SIM / "m233_t64_kernel.autotb.v"
RUNNER = SIM / "run_xsim.bat"
OUT = ROOT / "deployment" / "mage_vl4b" / "M233_T64_RTL_TIMEOUT_GATE_RESULT.json"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def fail(message: str) -> int:
    print(f"M233_RTL_TIMEOUT_EXPECTED_FAILURE_FAIL {message}", file=sys.stderr)
    return 1


def main() -> int:
    missing = [str(path) for path in (LOG, TB, RUNNER) if not path.is_file()]
    if missing:
        return fail("missing=" + ",".join(missing))

    log = LOG.read_text(encoding="utf-8", errors="replace")
    tb = TB.read_text(encoding="utf-8", errors="replace")
    runner = RUNNER.read_text(encoding="utf-8", errors="replace")
    requirements = {
        "timeout_marker": "M233_RTL_TIMEOUT_TRIGGERED finish_cnt=0 total=1" in log,
        "fatal_marker": "Fatal: M233 bounded timeout expired before ap_done" in log,
        "no_completed_transaction": "RTL Simulation : 1 / 1" not in log,
        "started_transaction": "RTL Simulation : 0 / 1" in log,
        "watchdog_budget_200_cycles": "repeat (200) @ (posedge AESL_clock);" in tb,
        "watchdog_checks_ap_done_proxy": "finish_cnt < AUTOTB_TRANSACTION_NUM" in tb,
        "watchdog_uses_fatal": "$fatal(1, \"M233 bounded timeout expired before ap_done\")" in tb,
        "runner_uses_original_uvm_timeout": "UVM_TIMEOUT=20000000000000" in runner,
    }
    failed = [name for name, passed in requirements.items() if not passed]
    if failed:
        return fail("requirements=" + ",".join(failed))

    match = re.search(r"Time:\s+(\d+)\s+ps", log)
    if not match:
        return fail("missing_fatal_time")
    fatal_time_ps = int(match.group(1))
    if not (0 < fatal_time_ps < 223_092_000):
        return fail(f"fatal_time_out_of_range={fatal_time_ps}")

    result = {
        "gate": "M233-T64-RTL-bounded-timeout-expected-failure",
        "status": "PASS",
        "build_id": "0x4D323333",
        "board_state_changed": False,
        "purpose": "Prove that the T64 RTL gate rejects a maximum-descriptor transaction that cannot reach ap_done within a bounded budget.",
        "watchdog_budget_cycles": 200,
        "fatal_time_ps": fatal_time_ps,
        "normal_max_descriptor_completion_time_ps": 223_092_000,
        "requirements": requirements,
        "evidence": {
            str(LOG.relative_to(ROOT)): {"sha256": sha256(LOG), "bytes": LOG.stat().st_size},
            str(TB.relative_to(ROOT)): {"sha256": sha256(TB), "bytes": TB.stat().st_size},
            str(RUNNER.relative_to(ROOT)): {"sha256": sha256(RUNNER), "bytes": RUNNER.stat().st_size},
        },
        "verified_at_utc": datetime.now(timezone.utc).isoformat(),
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    temp = OUT.with_suffix(OUT.suffix + ".tmp")
    temp.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    os.replace(temp, OUT)
    print(f"M233_RTL_TIMEOUT_EXPECTED_FAILURE_PASS fatal_time_ps={fatal_time_ps}")
    print(f"M233_RTL_TIMEOUT_GATE_RESULT={OUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
