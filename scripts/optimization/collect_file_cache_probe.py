import json
from pathlib import Path
from measurement import sha256,write_json,exclusive_lock
root=Path(__file__).resolve().parents[2];base=root/'deployment/mage_vl4b/optimization_v1'
log=root/'tmp/op01_file_cache_probe01/run.log';text=log.read_text(encoding='utf-8-sig')
if '__FILE_CACHE_RC_0__' not in text:raise RuntimeError('Probe not terminal/successful')
data=json.loads(text.split('FILE_CACHE_JSON_BEGIN',1)[1].split('FILE_CACHE_JSON_END',1)[0])
plan=base/'runs/OP01-file-cache-probe-01/plan.json'
if data['plan_sha256']!=sha256(plan) or data['script_sha256']!=sha256(root/'scripts/optimization/file_cache_probe.py'):
    raise RuntimeError('Probe identity mismatch')
if data['status']!='MEASURED' or len(data['records'])!=12 or not all(r['byte_exact'] for r in data['records']):
    raise RuntimeError('Probe incomplete')
if {(r['shard'],r['repeat']) for r in data['records']}!={(s,r) for s in range(4) for r in range(3)}:
    raise RuntimeError('Probe coverage mismatch')
out=base/'gates/G01-file-cache/attempt_01/result.json'
with exclusive_lock(base/'control.lock'):
    if out.exists():raise RuntimeError('Immutable result exists')
    write_json(out,dict(status='MEASURED',scope=data['scope'],board=data,log_sha256=sha256(log)))
    path=root/'deployment/mage_vl4b/BOARD_GATE_RESULT.json';index=json.loads(path.read_text(encoding='utf-8-sig'))
    index['latest_file_cache_probe']=dict(status='MEASURED',result=str(out.relative_to(root)),sha256=sha256(out),model_executed=False)
    write_json(path,index)
    path=base/'STATE.json';state=json.loads(path.read_text());state['results']['file_cache_probe']=str(out.relative_to(root))
    state['next_action']='Compare idle file cache microprobe with SYS05 read cost; instrument actual checkpoint replay cache/I/O without full-video rerun; same-quant layer0 gate_up remains required'
    write_json(path,state)
print(json.dumps([dict(shard=r['shard'],repeat=r['repeat'],read_s=r['read_s'],read_bytes=r['io_delta']['read_bytes'],residency_before=r['residency_before']) for r in data['records']]))
