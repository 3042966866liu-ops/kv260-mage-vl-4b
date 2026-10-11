#!/usr/bin/env python3
import hashlib,json,sys
from pathlib import Path
def H(p):return hashlib.sha256(p.read_bytes()).hexdigest()
p=Path(sys.argv[1]).resolve();h=sys.argv[2];me=sys.argv[3]
if H(Path(__file__))!=me:raise RuntimeError('M168 self hash mismatch')
r=Path('/home/ubuntu/tellme_m120_m89x2_20260901/results').resolve()
if p.parent.parent!=r or not p.parent.name.startswith('m167_corrected_layer0_') or p.name!='layer0_acceptance.json':raise RuntimeError('M168 predecessor path mismatch')
if not p.is_file() or H(p)!=h:raise RuntimeError('M168 predecessor hash mismatch')
v=json.loads(p.read_text())
m=v.get('measurement',{})
ok=v.get('gate')=='M144-M120-complete-layer0-boundary-acceptance' and v.get('status')=='PASS' and v.get('thresholds_frozen_before_board_measurement') is True and m.get('build_id')=='0x4d395832' and m.get('fpga_execution_proved') is True and m.get('expected_logical_calls')==5 and m.get('all_boundaries_finite') is True
if not ok:raise RuntimeError('M168 predecessor evidence mismatch')
print('M168_M167_LAYER0_PREDECESSOR_PASS')
