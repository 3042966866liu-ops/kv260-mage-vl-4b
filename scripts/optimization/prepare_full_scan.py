import json
from pathlib import Path
from measurement import sha256,write_json
root=Path(__file__).resolve().parents[2];base=root/'deployment/mage_vl4b/optimization_v1'
source=base/'gates/G01-SYS-development/attempt_05/board_result.json'
data=json.loads(source.read_text());observed=[r['current'] for r in data['transactions'][-162:]]
contracts=[];expected=[]
for name,kind in [('M126_LANGUAGE_RUNTIME_CONTRACT_RESULT.json','language_fourport'),('M126_LMHEAD_RUNTIME_CONTRACT_RESULT.json','lmhead_fourport')]:
    path=root/'deployment/mage_vl4b/m175_m120_fixed_text_candidate/contracts'/name
    c=json.loads(path.read_text());contracts.append(dict(name=name,kind=kind,sha256=sha256(path)))
    expected.extend(dict(chain_index=r['chain_index'],layer=r.get('layer'),family=r.get('family','lm_head')) for r in c['chains'])
if len(expected)!=162 or expected!=[{k:r.get(k) for k in ('chain_index','layer','family')} for r in observed]:
    raise RuntimeError('Contract order is not the observed incremental Decode sequence')
out=base/'runs/OP01-full-file-scan-01/plan.json'
if out.exists():raise RuntimeError('Immutable plan')
write_json(out,dict(source_sha256=sha256(source),contracts=contracts,expected_order=expected,
    expected_stage_bytes=2034890752,probe_dependency_sha256=sha256(root/'scripts/optimization/file_cache_probe.py')))
print('FULL_SCAN_ORDER_VERIFIED_162_CHAINS '+sha256(out))
