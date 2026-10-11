import json
from pathlib import Path
from measurement import sha256,write_json,exclusive_lock
root=Path(__file__).resolve().parents[2];base=root/'deployment/mage_vl4b/optimization_v1'
log=root/'tmp/op01_replay_import01/run.log';text=log.read_text(encoding='utf-8-sig')
if '__REPLAY_IMPORT_RC_0__' not in text:raise RuntimeError('Import not terminal success')
summary=json.loads(text.split('REPLAY_JSON_BEGIN',1)[1].split('REPLAY_JSON_END',1)[0])
manifest=base/'candidates/OP01-REPLAY-01/PACKAGE_MANIFEST.json'
if summary['status']!='PASS_IMPORT_RESTORE_ONLY' or summary['package_manifest_sha256']!=sha256(manifest) or summary['overlay_loads']!=0 or summary['input_token']!=1291 or summary['cache_before']!=852:
    raise RuntimeError('Import/restore scope mismatch')
out=base/'gates/G01-replay-import/attempt_01/result.json'
with exclusive_lock(base/'control.lock'):
    if out.exists():raise RuntimeError('Immutable result')
    write_json(out,dict(status='PASS_IMPORT_RESTORE_ONLY',summary=summary,uart_sha256=sha256(log),
        scope='Frozen runner import and actual checkpoint restore; summary-bound, not FPGA execution or numeric acceptance'))
    path=root/'deployment/mage_vl4b/BOARD_GATE_RESULT.json';index=json.loads(path.read_text(encoding='utf-8-sig'))
    index['latest_replay_import']=dict(status='PASS_IMPORT_RESTORE_ONLY',result=str(out.relative_to(root)),sha256=sha256(out),model_executed=False)
    write_json(path,index)
    path=base/'STATE.json';state=json.loads(path.read_text());state['results']['replay_import']=str(out.relative_to(root))
    state['next_action']='REPLAY01 imports and actual KV restore passed. Require same-COM3 sudo and fixed environment before one stable-hardware Decode; collect read I/O and layer0 gate_up capture; not full E2E.'
    write_json(path,state)
print('REPLAY_IMPORT_RESTORE_PASS_ONLY')
