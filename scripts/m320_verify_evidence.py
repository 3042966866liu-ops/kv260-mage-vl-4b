"""Verify the completed M320 software evidence; no model/board rerun."""
import hashlib
import json
import os
from pathlib import Path
root = Path(__file__).resolve().parents[1]
path = root/'deployment/mage_vl4b/M320_M120_TOKEN_ADAPTER_RESULT.json'
r = json.loads(path.read_text(encoding='utf-8'))
assert r['status']=='PASS_M120_SOFTWARE_INTERFACE_NOT_BOARD_OR_SEMANTIC_ACCEPTANCE'
assert r['board_execution_run'] is False and r['semantic_accuracy_passed'] is False
assert r['checkpoint']['blob_hash_verified'] is True and r['a8_hook_count']==253
assert r['identity']['status']=='PASS_EXACT_SOFTWARE_REFERENCE'
assert r['identity']['kv_lengths']==list(range(849,849+len(r['identity']['token_ids'])))
for name,expected in r['sources'].items():
    assert hashlib.sha256((root/name).read_bytes()).hexdigest()==expected, name
assert len(r['records'])==4
for fraction,n in ((.75,653),(.5,457)):
    rows=[x for x in r['records'] if x['fraction']==fraction]
    assert {x['method'] for x in rows}=={'uniform','content'}
    for x in rows:
        assert x['total_tokens']==n and len(x['visual_indices'])==n-65
        assert x['visual_indices']==sorted(set(x['visual_indices']))
        assert x['kv_lengths']==list(range(n,n+len(x['token_ids'])))
for name in r['sources']:
    if name.endswith('.py'):
        compile((root/name).read_text(encoding='utf-8'),name,'exec')
files=list(r['sources'])+['scripts/m320_run_m120_adapter_wsl.sh',
    'scripts/m320_verify_evidence.py','M320_M120_TOKEN_ADAPTER_REPORT.md',str(path.relative_to(root))]
files += [str(p.relative_to(root)) for p in sorted((root/'tmp/m320_session').glob('*.log'))]
result=dict(status='PASS_LOCAL_EVIDENCE_ONLY',board_execution_run=False,
            files=[dict(path=p,sha256=hashlib.sha256((root/p).read_bytes()).hexdigest()) for p in files])
out=root/'deployment/mage_vl4b/M320_LOCAL_EVIDENCE_VERIFICATION.json'
temp=out.with_suffix('.partial.json')
temp.write_text(json.dumps(result,indent=2),encoding='utf-8')
os.replace(temp,out)
print('M320_LOCAL_EVIDENCE_VERIFIED')
