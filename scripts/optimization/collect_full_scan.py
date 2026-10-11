import base64
import hashlib
import json
from pathlib import Path
import re
import zlib
from measurement import sha256,write_json,exclusive_lock
from full_file_scan import unique_bytes
root=Path(__file__).resolve().parents[2];base=root/'deployment/mage_vl4b/optimization_v1'
logs=root/'tmp/op01_full_file_scan01';text=(logs/'export.log').read_text(encoding='utf-8-sig');run=(logs/'run.log').read_text(encoding='utf-8-sig')
if '__FULL_SCAN_RC_0__' not in run or '__SCAN_EXPORT_RC_0__' not in text or 'SCAN_EXPORT_END' not in text:raise RuntimeError('Missing terminal proof')
summary=json.loads(run.split('FULL_SCAN_JSON_BEGIN',1)[1].split('FULL_SCAN_JSON_END',1)[0])
meta=json.loads(re.search(r'SCAN_EXPORT_META (.+)',text).group(1));chunks=re.findall(r'SCAN_EXPORT_CHUNK (\d+) ([A-Za-z0-9+/=]+)',text)
if [int(i) for i,v in chunks]!=list(range(len(chunks))):raise RuntimeError('Chunk order')
packed=base64.b64decode(''.join(v for i,v in chunks),validate=True)
if len(packed)!=meta['packed_bytes'] or hashlib.sha256(packed).hexdigest()!=meta['packed_sha256']:raise RuntimeError('Packed hash')
raw=zlib.decompress(packed)
if len(raw)!=meta['raw_bytes'] or hashlib.sha256(raw).hexdigest()!=meta['raw_sha256'] or meta['raw_sha256']!=summary['result_sha256']:raise RuntimeError('Raw hash')
data=json.loads(raw);plan=base/'runs/OP01-full-file-scan-01/plan.json'
if data['plan_sha256']!=sha256(plan) or data['script_sha256']!=sha256(root/'scripts/optimization/full_file_scan.py'):raise RuntimeError('Identity')
if data['status']!='MEASURED' or len(data['passes'])!=2 or len(data['windows'])!=648:raise RuntimeError('Scope')
if sum(r['bytes'] for r in data['windows'])!=2034890752 or unique_bytes(data['windows'])!=data['unique_bytes_per_pass']:raise RuntimeError('Byte accounting')
for p in data['passes']:
    if [r['index'] for r in p['records']]!=list(range(648)):raise RuntimeError('Read order')
    if abs(sum(r['read_ns'] for r in p['records'])/1e9-p['read_s'])>1e-9:raise RuntimeError('Read accounting')
if [r['sha256'] for r in data['passes'][0]['records']]!=[r['sha256'] for r in data['passes'][1]['records']]:raise RuntimeError('Scan bytes differ')
out=base/'gates/G01-full-file-scan/attempt_01'
with exclusive_lock(base/'control.lock'):
    out.mkdir(parents=True,exist_ok=False);(out/'board_result.json').write_bytes(raw)
    write_json(out/'result.json',dict(status='MEASURED',scope=data['scope'],board_result_sha256=sha256(out/'board_result.json'),
        uart_sha256=sha256(logs/'run.log'),export_sha256=sha256(logs/'export.log'),summary=summary))
    path=root/'deployment/mage_vl4b/BOARD_GATE_RESULT.json';index=json.loads(path.read_text(encoding='utf-8-sig'))
    index['latest_full_file_scan']=dict(status='MEASURED',result=str((out/'result.json').relative_to(root)),sha256=sha256(out/'result.json'),model_executed=False)
    write_json(path,index)
    path=base/'STATE.json';state=json.loads(path.read_text());state['results']['full_file_scan']=str((out/'result.json').relative_to(root))
    state['next_action']='Compare verified idle full-scan storage I/O and residency; use SYS05 checkpoint under actual runtime memory next, and same-quant real-family validation before changing inference'
    write_json(path,state)
print(json.dumps(summary))
