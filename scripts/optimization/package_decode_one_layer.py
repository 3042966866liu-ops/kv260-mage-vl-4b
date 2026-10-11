"""Build isolated layer A/B package reusing board-tested experimental overlay."""
import ast
import json
from pathlib import Path
from measurement import sha256,write_json

root=Path(__file__).resolve().parents[2]
base=root/'deployment/mage_vl4b/optimization_v1'
old=base/'candidates/OP01-decode-one-minimal-board-01'
out=base/'candidates/OP01-decode-one-layer-01'
if sha256(old/'PACKAGE_MANIFEST.json')!='1fb069ab95552b1c8f20fc8f4129ed10544c1e3e91c5869d7c41472466346442':
    raise RuntimeError('Pinned source package mismatch')
payload={}
for row in json.loads((old/'PACKAGE_MANIFEST.json').read_text())['files']:
    path=old/row['path']
    if sha256(path)!=row['sha256']:raise RuntimeError('Pinned file changed')
    if row['path'] not in ('decode_one_minimal_board.py','run_decode_one_minimal_board.sh'):
        payload[row['path']]=path.read_bytes()
for name in ('board_decode_one_layer.py','decode_one_runtime_adapter.py','decode_one_layer_probe.py',
             'decode_one_policy.py','decode_checkpoint.py','decode_trace.py','op01_support.py'):
    payload[name]=Path(__file__).with_name(name).read_bytes().replace(b'\r\n',b'\n')
payload['sys_config.json']=(base/'candidates/OP01-SYS-05/sys_config.json').read_bytes()
payload['checkpoint_plan.json']=(base/'runs/OP01-checkpoint-preflight-01/plan.json').read_bytes()
original=root/'deployment/mage_vl4b/m175_m120_fixed_text_candidate/runtime/board_runtime.py'
if sha256(original)!='5d53ea406e57de88f8c14d9bc4e1cb0c0049ff0b8f4bcf620e05745fcd82b201':
    raise RuntimeError('Stable board runtime changed')
payload['stable_base.py']=original.read_bytes()
candidate=payload['stable_base.py']
for a,b in ((b'BUILD_ID = 0x4D395832',b'BUILD_ID = 0x4F503131'),
            (b'self.overlay.mage_m120_m89x2_0',b'self.overlay.op01_decode_one_0')):
    if candidate.count(a)!=1:raise RuntimeError('Ambiguous runtime derivation')
    candidate=candidate.replace(a,b)
payload['candidate_base.py']=candidate
payload['run_layer.sh']=b'''#!/usr/bin/env bash
set -euo pipefail
here=$(cd -- "$(dirname -- "$0")" && pwd)
export PYTHONDONTWRITEBYTECODE=1 XILINX_XRT=/usr TMPDIR=/dev/shm
export PATH=/usr/local/share/pynq-venv/bin:/usr/local/bin:/usr/bin:/bin
export OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=4
exec /usr/local/share/pynq-venv/bin/python -B "$here/board_decode_one_layer.py" "$@"
'''
for name,raw in payload.items():
    if name.endswith('.py'):ast.parse(raw,filename=name)
out.mkdir(exist_ok=False)
rows=[]
for name,raw in payload.items():
    p=out/name;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(raw)
    rows.append(dict(path=name,bytes=len(raw),sha256=sha256(p)))
write_json(out/'PACKAGE_MANIFEST.json',dict(files=rows,file_count=len(rows),total_bytes=sum(x['bytes'] for x in rows),
    build_id='0x4F503131',formal_promotion_allowed=False,capacity_status='STOPPED_BY_USER_NOT_PASS',
    runtime_derivation='Only Build-ID constant and Overlay kernel attribute; adapter changes bit24 only for validated one-token dispatch'))
print(sha256(out/'PACKAGE_MANIFEST.json'))
