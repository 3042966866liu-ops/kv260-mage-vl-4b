"""Revalidate saved evidence without rerunning numerical or RTL calculations."""
import json
from pathlib import Path
from measurement import sha256, write_json

root=Path(__file__).resolve().parents[2]
base=root/'deployment/mage_vl4b/optimization_v1'
gates=['G02-decode-one-csim/attempt_01','G02-decode-one-real-csim/attempt_01',
       'G02-decode-one-boundary/attempt_02','G02-decode-one-rtl/attempt_01',
       'G02-decode-one-timeout/attempt_01','G02-decode-one-shapes/attempt_01']
checked={}
def check(relative, expected):
    path=(root/relative).resolve()
    path.relative_to(root)
    actual=sha256(path)
    if actual!=expected: raise RuntimeError('Evidence changed: '+relative)
    checked[path.relative_to(root).as_posix()]=actual

for name in gates:
    path=base/'gates'/name/'result.json'
    result=json.loads(path.read_text(encoding='utf-8-sig'))
    if not result['status'].startswith('PASS'):raise RuntimeError(name)
    check(str(path.relative_to(root)),sha256(path))
    for field in ['evidence','sources']:
        for relative, expected in result.get(field,{}).items():check(relative,expected)
for name in ['OP01-decode-one-header','OP01-decode-one-real-header',
             'OP01-decode-one-boundary-header-v2','OP01-decode-one-rtl-header',
             'OP01-decode-one-shapes-header']:
    path=base/'runs'/name/'result.json'
    result=json.loads(path.read_text(encoding='utf-8-sig'))
    if result['missing'] or result['status']!='PASS':raise RuntimeError(name)
    for item in result['files']:check(item['path'],item['sha256'])
    checked[path.relative_to(root).as_posix()]=sha256(path)
out=base/'runs/OP01-decode-one-prerequisite-audit/result.json'
if out.exists():raise RuntimeError('Immutable audit already exists')
write_json(out,dict(status='PASS_SAVED_IDENTITY_AUDIT_ONLY',checked_files=len(checked),
    evidence=checked,board_deployed=False,performance_pass=False,
    full_shell_authorized_by_this_audit=False,
    remaining_review='G06.2 maximum FIFO occupancy must be established, not inferred from configured depth or CSim stream depth. Existing normal RTL covers max-row output and descriptor count; need generated producer/consumer scheduling analysis or dynamic occupancy evidence.'))
print('PASS_SAVED_IDENTITY_AUDIT_ONLY checked_files='+str(len(checked)))
