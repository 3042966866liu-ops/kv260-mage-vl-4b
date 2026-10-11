import json
from pathlib import Path
from measurement import sha256,write_json,exclusive_lock
root=Path(__file__).resolve().parents[2];base=root/'deployment/mage_vl4b/optimization_v1'
log=root/'tmp/op01_lifecycle_import01/run.log';text=log.read_text(encoding='utf-8-sig')
if '__LIFECYCLE_IMPORT_RC_0__' not in text:raise RuntimeError('Import not terminal success')
summary=json.loads(text.split('REPLAY_JSON_BEGIN',1)[1].split('REPLAY_JSON_END',1)[0])
manifest=base/'candidates/OP01-LIFECYCLE-01/PACKAGE_MANIFEST.json'
if summary['status']!='PASS_IMPORT_RESTORE_ONLY' or summary['package_manifest_sha256']!=sha256(manifest) or summary['overlay_loads']!=0 or summary['input_token']!=1291 or summary['cache_before']!=852:
    raise RuntimeError('Import scope mismatch')
out=base/'gates/G01-lifecycle-import/attempt_01/result.json'
with exclusive_lock(base/'control.lock'):
    if out.exists():raise RuntimeError('Immutable result')
    write_json(out,dict(status='PASS_IMPORT_RESTORE_ONLY',summary=summary,uart_sha256=sha256(log),model_executed=False))
    path=root/'deployment/mage_vl4b/BOARD_GATE_RESULT.json';index=json.loads(path.read_text(encoding='utf-8-sig'))
    index['latest_lifecycle_import']=dict(status=summary['status'],result=str(out.relative_to(root)),sha256=sha256(out),model_executed=False)
    write_json(path,index)
    path=base/'STATE.json';state=json.loads(path.read_text())
    state['results']['lifecycle_import']=str(out.relative_to(root))
    state['next_action']='LIFECYCLE01 import passed; require same-COM3 sudo and fixed preflight, then actual visual-forward and three checkpoint Decode states. No performance acceptance.'
    write_json(path,state)
print('LIFECYCLE_IMPORT_PASS_ONLY')
