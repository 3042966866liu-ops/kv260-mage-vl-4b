#!/usr/bin/env python3
"""Synchronize the verified M166 corrected Layer-0 board-stage PASS."""

from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
RESULT_REL = "deployment/mage_vl4b/M166_M120_CORRECTED_LAYER0_BOARD_STAGE_RESULT_10.json"
EXPECTED_MANIFEST = "34662ca90cb45b9a1d34903538b030f28b1f9f70ece3f35e7ccbbaf6eb3bbf97"
EXPECTED_OUTPUT = "/home/ubuntu/tellme_m120_m89x2_20260901/m165_m120_layer0_board_candidate"


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def atomic_json(path: Path, value: dict) -> None:
    temporary = path.with_name(path.name + f".partial-{os.getpid()}")
    temporary.write_text(json.dumps(value, indent=2) + "\n", encoding="utf-8")
    os.replace(temporary, path)


def replace_marker(path: Path, start: str, end: str, body: str) -> None:
    text = path.read_text(encoding="utf-8")
    block = f"{start}\n{body.rstrip()}\n{end}\n\n"
    if start in text:
        before, rest = text.split(start, 1)
        _, after = rest.split(end, 1)
        text = before + block + after.lstrip("\r\n")
    else:
        lines = text.splitlines(keepends=True)
        insert = 1 if lines and lines[0].startswith("# ") else 0
        text = "".join(lines[:insert]) + ("\n" if insert else "") + block + "".join(lines[insert:])
    temporary = path.with_name(path.name + f".partial-{os.getpid()}")
    temporary.write_text(text, encoding="utf-8")
    os.replace(temporary, path)


def main() -> int:
    result_path = ROOT / RESULT_REL
    result = json.loads(result_path.read_text(encoding="utf-8"))
    if result.get("status") != "PASS" or result.get("candidate_build_id") != "0x4D395832":
        raise RuntimeError("M166 stage identity/status mismatch")
    if result.get("package_manifest_sha256") != EXPECTED_MANIFEST or result.get("output") != EXPECTED_OUTPUT:
        raise RuntimeError("M166 stage package identity mismatch")
    if result.get("file_count") != 18 or result.get("changed_files") != [
        "SOURCE_MANIFEST.json",
        "auxiliary/M77_TEXT_AUX_MANIFEST.json",
        "auxiliary/m77_text_aux_fp16.npz",
    ]:
        raise RuntimeError("M166 stage closure mismatch")
    if result.get("boot_dtb_cma_partitions_services_changed") is not False or result.get("stable_rollback_preserved") is not True:
        raise RuntimeError("M166 board-safety evidence mismatch")
    uart = Path(result["uart_log"])
    if not uart.is_absolute():
        uart = ROOT / uart
    if digest(uart) != result.get("uart_log_sha256"):
        raise RuntimeError("M166 UART log hash mismatch")
    uart_text = uart.read_text(encoding="utf-8", errors="replace")
    for marker in ("M166_CORRECTED_LAYER0_STAGE_PASS", "__M166_STAGE_RESULT_BEGIN__", "__M166_STAGE_RESULT_END__"):
        if marker not in uart_text:
            raise RuntimeError(f"M166 UART marker missing: {marker}")

    board_path = ROOT / "deployment/mage_vl4b/BOARD_GATE_RESULT.json"
    board = json.loads(board_path.read_text(encoding="utf-8"))
    board["status"] = "M166_M120_CORRECTED_LAYER0_STAGE_PASS_M167_PENDING"
    board["candidate_build_id"] = "0x4D395832"
    board["full_model_deployed"] = False
    board["web_deployed"] = False
    board["stable_rollback_preserved"] = True
    board["latest_m166_corrected_layer0_stage"] = {
        **result,
        "formal_result": RESULT_REL,
        "formal_result_sha256": digest(result_path),
        "delta_manifest_sha256": "446a409b9a840487135c406773e044d4450b1c87e501bea6366a81daef774273",
        "transport_corrections": [
            "receiver stored outside the declared delta closure",
            "both auxiliary members streamed under fixed path/size/SHA-256 whitelist",
            "sudo -n preflight runs before transfer",
            "already-captured UART completion markers are recognized without timeout",
        ],
    }
    board["next_gate"] = "Run only M167 complete Layer-0 against the M166 corrected candidate; fixed-text remains locked."
    atomic_json(board_path, board)

    body = f"""## M164--M166: corrected M120 Layer-0 candidate is staged on KV260 (2026-09-01)

- M164 remains a real FPGA Layer-0 FAIL caused by legacy M77 FP16 selected embedding rows being used before the first FPGA linear call; it is retained as rejected evidence.
- M165 replaced exactly those 23 rows with M120 W3-G64-derived FP16 rows; its offline first-boundary precheck is relative-L2 `0.002434347` and cosine `0.999997062`.
- M166 attempt 10 passed on the board. The corrected 18-file package was atomically generated at `{EXPECTED_OUTPUT}` with package-manifest SHA-256 `{EXPECTED_MANIFEST}`. Only `SOURCE_MANIFEST.json` and the two fixed-text auxiliary files changed.
- The delta closure and both auxiliary identities were reverified over COM3. Earlier closure and expired-sudo control attempts did not generate a candidate. The final controller now checks `sudo -n` before transfer and uses line-streamed, exact path/size/hash-whitelisted members.
- Boot, DTB, CMA, partitions, services and stable rollback were not changed. This is package staging only, not a Layer-0, fixed-text, full-model, performance, video or Web PASS.
- Next gate: run only M167 complete Layer-0 against this corrected candidate; fixed-text remains locked until M167 passes.

Evidence: `{RESULT_REL}` (SHA-256 `{digest(result_path)}`), UART log SHA-256 `{result['uart_log_sha256']}`."""
    replace_marker(ROOT / "CURRENT_STATE.md", "<!-- M164_M166_SYNC_START -->", "<!-- M164_M166_SYNC_END -->", body)
    replace_marker(ROOT / "docsMILESTONES.md", "<!-- M164_M166_SYNC_START -->", "<!-- M164_M166_SYNC_END -->", body.replace("## M164--M166:", "## M164--M166："))
    print(json.dumps({
        "status": "PASS",
        "m166_result_sha256": digest(result_path),
        "board_gate_result_sha256": digest(board_path),
    }, indent=2))
    print("M173_M166_STAGE_PASS_STATE_SYNC_PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
