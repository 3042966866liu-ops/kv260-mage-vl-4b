#!/usr/bin/env python3
import hashlib,sys
from pathlib import Path
p=Path(sys.argv[1]).resolve();h=sys.argv[2]
if hashlib.sha256(Path(__file__).read_bytes()).hexdigest()!=h:raise RuntimeError('M168 self hash mismatch')
r=Path('/home/ubuntu/tellme_m120_m89x2_20260901/results').resolve()
if p.parent!=r or not p.name.startswith('m168_fixed_text_'):raise RuntimeError('M168 result path mismatch')
if p.exists():raise RuntimeError('M168 result path exists')
print('M168_RESULT_DIR_ABSENT')
