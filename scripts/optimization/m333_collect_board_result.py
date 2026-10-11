#!/usr/bin/env python3
"""Extract the exact M333 board JSON from COM3 and verify its board-side SHA."""

import hashlib
import json
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[2]
LOG = ROOT / "tmp/m333/board_cpu_http_gate.log"
HASH_LOG = ROOT / "tmp/m333/board_result_hash.log"
OUT = ROOT / "deployment/mage_vl4b/optimization_v1/runs/M333-web-review-loop-board-01/BOARD_RESULT.json"

raw = LOG.read_text(encoding="utf-8")
matches = re.findall(r"M333_BOARD_RESULT_BEGIN\s*(\{[^\r\n]+\})\s*M333_BOARD_RESULT_END", raw)
if len(matches) != 1 or "__M75C_UART_RC_0__" not in raw:
    raise RuntimeError("missing or ambiguous successful board result")
value = json.loads(matches[0])
if value.get("gate") != "M333-KV260-CPU-only-fake-runtime":
    raise RuntimeError("wrong gate identity")
encoded = (json.dumps(value, indent=2, ensure_ascii=False) + "\n").encode("utf-8")
digest = hashlib.sha256(encoded).hexdigest()
hash_log = HASH_LOG.read_text(encoding="utf-8")
if f"{digest}  /home/ubuntu/m333_offline_board_01/BOARD_RESULT.json" not in hash_log:
    raise RuntimeError("board and local result SHA mismatch")
if OUT.exists() and OUT.read_bytes() != encoded:
    raise FileExistsError("refusing to overwrite different board result")
OUT.write_bytes(encoded)
print(json.dumps({"result": str(OUT), "sha256": digest,
                  "status": value["status"]}))
