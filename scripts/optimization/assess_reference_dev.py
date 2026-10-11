"""Assess one controlled development answer; never infer dataset accuracy."""
import json
from pathlib import Path
import numpy as np
from measurement import sha256,write_json,exclusive_lock

ROOT=Path(__file__).resolve().parents[2]
BASE=ROOT/'deployment/mage_vl4b/optimization_v1'
dataset=BASE/'datasets/dev_bootstrap_v1'
truth_path=dataset/'truth_dev.json'
truth=json.loads(truth_path.read_text())['samples'][0]
frames=np.load(dataset/'board_reference_v1/dev-0001_rgb.npy',allow_pickle=False)
centers=[]
for frame in frames:
    rgb=frame.astype(np.int16)
    mask=(rgb[:,:,0]>150)&(rgb[:,:,0]-rgb[:,:,1]>80)&(rgb[:,:,0]-rgb[:,:,2]>80)
    y,x=np.nonzero(mask)
    if len(x)<100:raise RuntimeError('Insufficient controlled red pixels')
    centers.append(float(x.mean()))
if not all(a<b for a,b in zip(centers,centers[1:])):
    raise RuntimeError('Decoded visual movement does not match render truth')
records=[]
for name in ('OP01-software-reference-dev0001-v1','OP01-official-reference-dev0001-v1'):
    path=BASE/'runs'/name/'result.json'
    if not path.exists():continue
    item=json.loads(path.read_text())
    if item['status']=='RUNNING':continue
    answer=item.get('answer','').strip().lower().rstrip('.')
    records.append(dict(run=name,result_sha256=sha256(path),execution_status=item['status'],
        answer=item.get('answer'),expected=truth['answer'],correct=answer==truth['answer'],
        valid_tokens=len(item.get('valid_token_ids',[])),input_sha256=item.get('input_sha256'),
        prompt_sha256=item.get('prompt_sha256'),rgb_sha256=item.get('rgb_sha256')))
if not records:raise RuntimeError('No terminal reference')
if len(records)==2:
    for key in ('input_sha256','prompt_sha256','rgb_sha256'):
        if records[0][key]!=records[1][key]:raise RuntimeError('Reference input differs: '+key)
out=BASE/'gates/G01-reference-dev'/('attempt_02' if len(records)==2 else 'attempt_01')/'result.json'
if out.exists():raise RuntimeError('Immutable assessment exists')
result=dict(status='MEASURED',scope='One controlled development motion input; not formal G01/quality gate',
    truth_sha256=sha256(truth_path),decoded_red_centers_x=centers,references=records,
    board_executed=False,formal_quality_pass=False,numerical_acceptance=False,
    next_action='Resolve software quality/input/reference discrepancy before accepting compressed or full SYS quality')
with exclusive_lock(BASE/'control.lock'):
    write_json(out,result)
    path=BASE/'STATE.json';state=json.loads(path.read_text())
    state['results']['software_reference_dev']=str(out.relative_to(ROOT))
    state['next_action']=result['next_action']
    write_json(path,state)
print(json.dumps(result,allow_nan=False))
