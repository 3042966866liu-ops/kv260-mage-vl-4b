#!/usr/bin/env python3
import hashlib,sys
from pathlib import Path
p=Path(sys.argv[1]).resolve(); h=sys.argv[2]
if hashlib.sha256(Path(__file__).read_bytes()).hexdigest()!=h:raise RuntimeError('M167 self hash mismatch')
root=Path('/home/ubuntu/tellme_m120_m89x2_20260901/results').resolve()
if p.parent!=root or not p.name.startswith('m167_corrected_layer0_'):raise RuntimeError('M167 result path mismatch')
if p.exists():raise RuntimeError('M167 result path exists')
print('M167_RESULT_DIR_ABSENT')
