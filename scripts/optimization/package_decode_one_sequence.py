"""Freeze three-step continuation after exact complete single-step board gate."""
import ast
import json
from pathlib import Path
from measurement import sha256,write_json

root=Path(__file__).resolve().parents[2]
base=root/'deployment/mage_vl4b/optimization_v1'
old=base/'candidates/OP01-decode-one-ab-01'
out=base/'candidates/OP01-decode-one-sequence-01'
evidence=base/'runs/OP01-decode-one-ab-candidate-01/result.json'
proof=json.loads(evidence.read_text())
if proof['status']!='PASS_CANDIDATE_DECODE_EXACT' or not proof['stable_restored']:
    raise RuntimeError('Exact single-step prerequisite missing')
if sha256(old/'PACKAGE_MANIFEST.json')!='4468af81c47d58352153ffccf5158192c4eb6e8012b0202cf07930839e3edbff':
    raise RuntimeError('Predecessor drift')
payload={}
for row in json.loads((old/'PACKAGE_MANIFEST.json').read_text())['files']:
    p=old/row['path']
    if sha256(p)!=row['sha256']:raise RuntimeError('Member drift')
    payload[row['path']]=p.read_bytes()
for name in ('board_decode_one_layer.py','decode_one_sequence.py','test_decode_one_sequence.py'):
    payload[name]=Path(__file__).with_name(name).read_bytes().replace(b'\r\n',b'\n')
payload['single_step_gate.json']=evidence.read_bytes()
if payload['run_layer.sh'].count(b'--full-decode')!=1:raise RuntimeError('Runner drift')
payload['run_layer.sh']=payload['run_layer.sh'].replace(b'--full-decode',b'--full-decode --sequence')
for name,raw in payload.items():
    if name.endswith('.py'):ast.parse(raw,filename=name)
out.mkdir(exist_ok=False);rows=[]
for name,raw in payload.items():
    p=out/name;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(raw)
    rows.append(dict(path=name,bytes=len(raw),sha256=sha256(p)))
write_json(out/'PACKAGE_MANIFEST.json',dict(files=rows,file_count=len(rows),
    total_bytes=sum(x['bytes'] for x in rows),build_id='0x4F503131',
    formal_promotion_allowed=False,capacity_status='STOPPED_BY_USER_NOT_PASS',
    scope='Three consecutive Decode steps, not formal throughput',
    prerequisite_sha256=sha256(evidence)))
print(sha256(out/'PACKAGE_MANIFEST.json'))
