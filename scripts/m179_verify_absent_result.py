#!/usr/bin/env python3
import hashlib
import sys
from pathlib import Path

path = Path(sys.argv[1]).resolve()
self_hash = sys.argv[2]
if hashlib.sha256(Path(__file__).read_bytes()).hexdigest() != self_hash:
    raise RuntimeError("M179 self hash mismatch")
root = Path("/home/ubuntu/tellme_m120_m89x2_20260901/results").resolve()
if path.parent != root or not path.name.startswith("m179_fixed_text_"):
    raise RuntimeError("M179 result path mismatch")
if path.exists():
    raise RuntimeError("M179 result path exists")
print("M179_RESULT_DIR_ABSENT")
