import json
from pathlib import Path
from measurement import sha256,write_json,exclusive_lock
root=Path(__file__).resolve().parents[2];base=root/'deployment/mage_vl4b/optimization_v1'
log=root/'tmp/op01_transfer_identity/verified.log';text=log.read_text(encoding='utf-8-sig')
assert '__TRANSFER_IDENTITY_RC_0__' in text
data=json.loads(text.split('TRANSFER_IDENTITY_JSON_BEGIN',1)[1].split('TRANSFER_IDENTITY_JSON_END',1)[0])
assert data['instrument_created'] and data['source_sha256']=='56825701b6bda461c87340986bd67165a7bca59d7652a055bbb7bb2d8b3597d9'
out=base/'gates/G01-transfer-identity/attempt_01/result.json'
with exclusive_lock(base/'control.lock'):
    if out.exists():raise RuntimeError('Immutable result exists')
    write_json(out,dict(status='PASS',scope='Source identity and instrument compilation only',
        overlay_loaded=False,model_executed=False,board=data,log_sha256=sha256(log)))
    path=root/'deployment/mage_vl4b/BOARD_GATE_RESULT.json';index=json.loads(path.read_text(encoding='utf-8-sig'))
    index['latest_transfer_identity']=dict(status='PASS',result=str(out.relative_to(root)),sha256=sha256(out),model_executed=False)
    write_json(path,index)
    path=base/'STATE.json';state=json.loads(path.read_text());state['results']['transfer_identity']=str(out.relative_to(root))
    state['next_action']='Transfer source identity/compile verified on board. Freeze corrected candidate and rerun imports only; no repeated SYS/E2E until diagnostic prerequisites accepted.'
    write_json(path,state)
print('TRANSFER_SOURCE_IDENTITY_AND_COMPILE_PASS_ONLY')
