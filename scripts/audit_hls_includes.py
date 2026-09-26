#!/usr/bin/env python3
"""Check quoted relative HLS include closure; does not compile or run RTL."""

from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1] / "hls"


def main() -> int:
    checked = 0
    missing = []
    for source in sorted(ROOT.rglob("*")):
        if source.suffix not in (".cpp", ".hpp", ".h") or not source.is_file():
            continue
        for target in re.findall(r'^\s*#\s*include\s+"([^"]+)"', source.read_text(encoding="utf-8", errors="replace"), re.M):
            checked += 1
            if not (source.parent / target).is_file():
                missing.append(f"{source.relative_to(ROOT)} -> {target}")
    print(f"HLS_INCLUDE_CLOSURE checked={checked} missing={len(missing)}")
    for item in missing:
        print("MISSING", item)
    return 0 if not missing else 1


if __name__ == "__main__":
    raise SystemExit(main())
