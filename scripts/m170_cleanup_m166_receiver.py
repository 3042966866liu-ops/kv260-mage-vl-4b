#!/usr/bin/env python3
import hashlib,sys
from pathlib import Path
p=Path('/home/ubuntu/tellme_m120_m89x2_20260901/m166_delta_01/m166_uart_file_receiver.py')
expected='94718115c8d1533be54f7787d044fca57d8c312f766f9b018e0f33a8b94c146f'
me=sys.argv[1]
H=lambda x:hashlib.sha256(x.read_bytes()).hexdigest()
if H(Path(__file__))!=me:raise RuntimeError('M170 self hash mismatch')
if not p.is_file() or H(p)!=expected:raise RuntimeError('M170 target identity mismatch')
p.unlink()
if p.exists():raise RuntimeError('M170 cleanup failed')
print('M170_M166_EXACT_RECEIVER_CLEANUP_PASS')
