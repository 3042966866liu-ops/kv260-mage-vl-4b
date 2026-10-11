"""Freeze complete Decode A/B runner after real-layer exact gate."""
import ast
import json
from pathlib import Path
from measurement import sha256,write_json
root=Path(__file__).resolve().parents[2];base=root/'deployment/mage_vl4b/optimization_v1'
layer=base/'candidates/OP01-decode-one-layer-01';out=base/'candidates/OP01-decode-one-ab-01'
evidence=base/'runs/OP01-decode-one-layer-candidate-01/result.json'
proof=json.loads(evidence.read_text())
if proof['status']!='PASS_CANDIDATE_LAYER_EXACT' or not proof['stable_restored']:raise RuntimeError('Layer gate required')
if sha256(layer/'PACKAGE_MANIFEST.json')!='4e7226a240b8daca0c29b529910467e30f13a378bbe08a471b61d67ceaeeb5a3':raise RuntimeError('Layer package drift')
payload={}
for row in json.loads((layer/'PACKAGE_MANIFEST.json').read_text())['files']:
    p=layer/row['path']
    if sha256(p)!=row['sha256']:raise RuntimeError('Layer member drift')
    payload[row['path']]=p.read_bytes()
for name in ('board_decode_one_layer.py','decode_diagnostic.py','decode_io_trace.py','lifecycle_reads.py',
             'summarize_decode_trace.py','transfer_trace.py'):
    payload[name]=Path(__file__).with_name(name).read_bytes().replace(b'\r\n',b'\n')
payload['lifecycle_read_plan.json']=(base/'candidates/OP01-LIFECYCLE-01/lifecycle_read_plan.json').read_bytes()
payload['layer_gate.json']=evidence.read_bytes()
payload['run_layer.sh']=payload['run_layer.sh'].replace(b'"$@"',b'--full-decode "$@"')
for name,raw in payload.items():
    if name.endswith('.py'):ast.parse(raw,filename=name)
out.mkdir(exist_ok=False);rows=[]
for name,raw in payload.items():
    p=out/name;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(raw)
    rows.append(dict(path=name,bytes=len(raw),sha256=sha256(p)))
write_json(out/'PACKAGE_MANIFEST.json',dict(files=rows,file_count=len(rows),total_bytes=sum(x['bytes'] for x in rows),
    build_id='0x4F503131',formal_promotion_allowed=False,capacity_status='STOPPED_BY_USER_NOT_PASS',
    layer_gate_sha256=sha256(evidence),scope='Matched KV852 one-step diagnostic; not formal throughput'))
print(sha256(out/'PACKAGE_MANIFEST.json'))
