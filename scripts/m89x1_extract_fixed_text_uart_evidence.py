#!/usr/bin/env python3
"""Extract fixed-text environment and E2E JSON objects from one UART log."""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path


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
    parser.add_argument("--environment", type=Path, required=True)
    parser.add_argument("--measurement", type=Path, required=True)
    parser.add_argument("--measurement-gate", default="M89-X-fixed-text-E2E")
    args = parser.parse_args()
    environment = None
    measurement = None
    for payload in objects(args.log.read_text(encoding="utf-8", errors="replace")):
        gate = payload.get("gate") if isinstance(payload, dict) else None
        if gate == "M89-X1-board-environment":
            environment = payload
        elif gate == args.measurement_gate:
            measurement = payload
    if environment is None or measurement is None:
        raise RuntimeError("missing fixed-text UART result objects")
    if (environment.get("status") != "PASS"
            or measurement.get("status") not in {"PASS", "FAIL", "MEASURED"}):
        raise RuntimeError("unexpected fixed-text UART result statuses")
    atomic_json(args.environment, environment)
    atomic_json(args.measurement, measurement)
    print(f"M89X1_FIXED_TEXT_UART_EVIDENCE_EXTRACT_PASS status={measurement['status']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
