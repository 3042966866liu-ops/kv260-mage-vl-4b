import json
from pathlib import Path
from measurement import sha256,write_json,exclusive_lock
root=Path(__file__).resolve().parents[2];base=root/'deployment/mage_vl4b/optimization_v1'
log=root/'tmp/op01_checkpoint_preflight01/run.log';text=log.read_text(encoding='utf-8-sig')
if '__CHECKPOINT_RC_0__' not in text:raise RuntimeError('Not terminal success')
data=json.loads(text.split('CHECKPOINT_JSON_BEGIN',1)[1].split('CHECKPOINT_JSON_END',1)[0])
plan=base/'runs/OP01-checkpoint-preflight-01/plan.json';expected=json.loads(plan.read_text())
if data['plan_sha256']!=sha256(plan) or data['script_sha256']!=sha256(root/'scripts/optimization/checkpoint_preflight.py'):raise RuntimeError('Identity')
if data['status']!='RESTORED' or data['manifest_sha256']!=expected['checkpoint_manifest_sha256'] or data['arrays_verified']!=72 or data['kv_length']!=852 or data['next_token']!=1291:
    raise RuntimeError('Wrong restored state')
out=base/'gates/G01-checkpoint-restore/attempt_01/result.json'
with exclusive_lock(base/'control.lock'):
    if out.exists():raise RuntimeError('Immutable result')
    write_json(out,dict(status='RESTORED',scope=data['scope'],board=data,uart_sha256=sha256(log),numerical_acceptance=False))
    path=root/'deployment/mage_vl4b/BOARD_GATE_RESULT.json';index=json.loads(path.read_text(encoding='utf-8-sig'))
    index['latest_checkpoint_restore']=dict(status='RESTORED',result=str(out.relative_to(root)),sha256=sha256(out),model_executed=False)
    write_json(path,index)
    path=base/'STATE.json';state=json.loads(path.read_text());state['results']['checkpoint_restore']=str(out.relative_to(root))
    state['next_action']='Real SYS05 checkpoint restore verified72arrays/251265024bytes/KV852/token1291. Prepare isolated language-runtime replay with read I/O trace and real layer0 gate_up capture; imports/preflight before overlay; no full video rerun.'
    write_json(path,state)
print('REAL_KV_RESTORE_VERIFIED_ONLY')
