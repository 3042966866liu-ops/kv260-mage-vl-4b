import json
from pathlib import Path
from measurement import sha256,write_json,exclusive_lock
root=Path(__file__).resolve().parents[2];base=root/'deployment/mage_vl4b/optimization_v1'
log=root/'tmp/op01_diagnostic_smoke/run.log';text=log.read_text(encoding='utf-8-sig')
assert '__DIAGNOSTIC_SMOKE_RC_0__' in text
data=json.loads(text.split('DIAGNOSTIC_SMOKE_JSON_BEGIN',1)[1].split('DIAGNOSTIC_SMOKE_JSON_END',1)[0])
assert data['status']=='PASS_SOFTWARE_SMOKE_ONLY' and data['byte_exact'] and data['checkpoint_exact']
assert data['short_read_rejected'] and data['sync_count']==1
assert not data['overlay_loaded'] and not data['model_executed']
out=base/'gates/G01-diagnostic-smoke/attempt_01/result.json'
with exclusive_lock(base/'control.lock'):
    if out.exists():raise RuntimeError('Immutable gate exists')
    write_json(out,dict(status='PASS_SOFTWARE_ONLY',board=data,log_sha256=sha256(log),
        scope='Target-Python synthetic ordinary-memory smoke; not CMA or real model numerical validation'))
    path=root/'deployment/mage_vl4b/BOARD_GATE_RESULT.json';index=json.loads(path.read_text(encoding='utf-8-sig'))
    index['latest_diagnostic_smoke']=dict(status='PASS_SOFTWARE_ONLY',result=str(out.relative_to(root)),sha256=sha256(out))
    write_json(path,index)
    path=base/'STATE.json';state=json.loads(path.read_text());state['results']['diagnostic_smoke']=str(out.relative_to(root))
    state['next_action']='Actual SYS05 diagnostic checkpoint acquisition after same-terminal sudo/preflight. One fixed-input reconstruction is required because SYS02 did not save KV; not a performance acceptance run.'
    write_json(path,state)
print('DIAGNOSTIC_SMOKE_EVIDENCE_COLLECTED')
