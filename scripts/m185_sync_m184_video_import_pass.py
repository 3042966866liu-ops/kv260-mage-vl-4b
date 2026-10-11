#!/usr/bin/env python3
"""Synchronize the exact M184 board-import PASS into authoritative state."""

from __future__ import annotations

import hashlib
import json
import os
import sys
from pathlib import Path


sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parents[1]
M184_REL = "deployment/mage_vl4b/M184_M181_VIDEO_BOARD_IMPORT_RESULT_01.json"
M182_SHA = "da6c69cb91a3956def857616f16d45358dd909b90967e110ad7e3a451b7e4f50"
PACKAGE_SHA = "1596536bfe6865cb7eab5c038d8b4da8b666afc7cbd629ddc4559781727151d6"
DESTINATION = "/home/ubuntu/tellme_m120_m89x2_20260901/m181_m120_video_board_candidate"


def digest(path: Path) -> str:
    value = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(4 << 20), b""):
            value.update(block)
    return value.hexdigest()


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
    result_path = ROOT / M184_REL
    result = json.loads(result_path.read_text(encoding="utf-8"))
    if result.get("gate") != "M184-M181-video-direct-Ethernet-board-import" or result.get("status") != "PASS":
        raise RuntimeError("M185 M184 gate/status mismatch")
    if result.get("package_manifest_sha256") != PACKAGE_SHA or result.get("m182_result_sha256") != M182_SHA:
        raise RuntimeError("M185 M184 package/predecessor mismatch")
    if result.get("destination") != DESTINATION or int(result.get("file_count", -1)) != 50 or int(result.get("total_bytes", -1)) != 1_649_266_450:
        raise RuntimeError("M185 M184 closure mismatch")
    if result.get("boot_dtb_cma_partitions_services_changed") is not False or result.get("stable_rollback_preserved") is not True:
        raise RuntimeError("M185 M184 stable-state mismatch")

    board_path = ROOT / "deployment/mage_vl4b/BOARD_GATE_RESULT.json"
    board = json.loads(board_path.read_text(encoding="utf-8"))
    offline = board.get("latest_m120_video_offline_candidate", {})
    if offline.get("formal_result_sha256") != M182_SHA or offline.get("package_manifest_sha256") != PACKAGE_SHA:
        raise RuntimeError("M185 authoritative M182 predecessor mismatch")
    board["status"] = "M184_M120_VIDEO_PACKAGE_BOARD_IMPORT_PASS_PS_VISION_PENDING"
    board["full_model_deployed"] = False
    board["web_deployed"] = False
    board["stable_rollback_preserved"] = True
    board["latest_m120_video_board_import"] = {
        **result,
        "formal_result": M184_REL,
        "formal_result_sha256": digest(result_path),
        "scope_boundary": "Hash-verified board package transfer only; PS vision and video-language E2E have not run.",
    }
    board["next_gate"] = "Run only the fixed four-frame PS BF16/W4 vision numerical gate on the KV260; do not run full video E2E unless it passes."
    atomic_json(board_path, board)

    body = f"""## M184/M185: M181 video candidate transferred and atomically verified on KV260 (2026-09-01)

- COM3 first proved `sudo -n true` in the same authorized terminal and verified the four-member receiver bootstrap (manifest SHA-256 `49e1bf51416426af9a31f674d161666d51a9b9d018e4a032c8ca9fc16aaca15d`).
- The PC then made an outbound direct-Ethernet connection to the temporary board endpoint `192.168.0.2:8767`; SSH was not used. The temporary address was removed by the versioned runner on exit.
- All `50` transported files totaling `1,649,266,450` bytes were checked while receiving and reread for SHA-256 on the board. The nested M181 package manifest matched `{PACKAGE_SHA}` and the staging directory was atomically published to `{DESTINATION}`.
- This PASS proves only exact package presence on the board. PS vision computation and video-language FPGA E2E have not run; `full_model_deployed=false` and `web_deployed=false` remain authoritative.
- No boot, DTB, CMA, partition, service or stable rollback state changed. The next gate is only the fixed four-frame PS BF16/W4 vision numerical comparison.

Evidence: `{M184_REL}` (SHA-256 `{digest(result_path)}`), UART log SHA-256 `{result['uart_log_sha256']}`."""
    replace_marker(ROOT / "CURRENT_STATE.md", "<!-- M184_VIDEO_IMPORT_PASS_START -->", "<!-- M184_VIDEO_IMPORT_PASS_END -->", body)
    replace_marker(ROOT / "docsMILESTONES.md", "<!-- M184_VIDEO_IMPORT_PASS_START -->", "<!-- M184_VIDEO_IMPORT_PASS_END -->", body.replace("## M184/M185:", "## M184/M185："))
    print(json.dumps({"status": "PASS", "m184_result_sha256": digest(result_path), "board_gate_result_sha256": digest(board_path)}, indent=2))
    print("M185_M184_VIDEO_IMPORT_STATE_SYNC_PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
