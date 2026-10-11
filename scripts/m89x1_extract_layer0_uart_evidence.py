#!/usr/bin/env python3
"""Extract the two complete JSON results from an M89-X1 Layer-0 UART log."""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path


TARGETS = {
    "M89-X1-layer0-full-transformer-tolerance-diagnostic": "measurement",
    "M89-X1-HS64-complete-layer0-numerical-acceptance": "formal",
}


def objects(text: str):
    start = None
    depth = 0
    quoted = False
    escaped = False
    for index, char in enumerate(text):
        if start is None:
            if char == "{":
                start, depth, quoted, escaped = index, 1, False, False
            continue
        if quoted:
            if escaped:
                escaped = False
            elif char == "\\":
                escaped = True
            elif char == '"':
                quoted = False
        elif char == '"':
            quoted = True
        elif char == "{":
            depth += 1
        elif char == "}":
            depth -= 1
            if depth == 0:
                raw = text[start:index + 1]
                start = None
                try:
                    yield json.loads(raw)
                except json.JSONDecodeError:
                    pass


def atomic_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    os.replace(temporary, path)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--log", type=Path, required=True)
    parser.add_argument("--measurement", type=Path, required=True)
    parser.add_argument("--formal", type=Path, required=True)
    args = parser.parse_args()
    found = {}
    for payload in objects(args.log.read_text(encoding="utf-8", errors="replace")):
        gate = payload.get("gate") if isinstance(payload, dict) else None
        if gate in TARGETS:
            found[TARGETS[gate]] = payload
    if set(found) != {"measurement", "formal"}:
        raise RuntimeError(f"missing UART result objects: {sorted(set(TARGETS.values()) - set(found))}")
    if (found["measurement"].get("status") != "MEASURED"
            or found["formal"].get("status") not in {"PASS", "FAIL"}):
        raise RuntimeError("unexpected Layer-0 result statuses")
    atomic_json(args.measurement, found["measurement"])
    atomic_json(args.formal, found["formal"])
    print(f"M89X1_HS64_LAYER0_UART_EVIDENCE_EXTRACT_PASS status={found['formal']['status']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
