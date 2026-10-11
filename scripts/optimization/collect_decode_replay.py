import base64
import hashlib
import json
from pathlib import Path
import re
import zlib
from measurement import sha256,write_json,exclusive_lock
from summarize_decode_trace import summarize
from replay_io_summary import read_io_summary
root=Path(__file__).resolve().parents[2];base=root/'deployment/mage_vl4b/optimization_v1'
logs=root/'tmp/op01_replay01';text=(logs/'export.log').read_text(encoding='utf-8-sig');run=(logs/'run.log').read_text(encoding='utf-8-sig')
if not re.search(r'__REPLAY_RC_[01]__',run) or '__REPLAY_EXPORT_RC_0__' not in text or 'REPLAY_EXPORT_END' not in text:
    raise RuntimeError('Missing terminal proof')
summary=json.loads(run.split('REPLAY_JSON_BEGIN',1)[1].split('REPLAY_JSON_END',1)[0])
meta=json.loads(re.search(r'REPLAY_EXPORT_META (.+)',text).group(1));chunks=re.findall(r'REPLAY_EXPORT_CHUNK (\d+) ([A-Za-z0-9+/=]+)',text)
if [int(i) for i,v in chunks]!=list(range(len(chunks))):raise RuntimeError('Chunk order')
packed=base64.b64decode(''.join(v for i,v in chunks),validate=True)
if len(packed)!=meta['packed_bytes'] or hashlib.sha256(packed).hexdigest()!=meta['packed_sha256']:raise RuntimeError('Packed hash')
raw=zlib.decompress(packed)
if len(raw)!=meta['raw_bytes'] or hashlib.sha256(raw).hexdigest()!=meta['raw_sha256'] or meta['raw_sha256']!=summary['full_result_sha256']:raise RuntimeError('Raw hash')
data=json.loads(raw)
if data['package_manifest_sha256']!=sha256(base/'candidates/OP01-REPLAY-01/PACKAGE_MANIFEST.json'):raise RuntimeError('Candidate identity')
interpretation=dict(numerical_acceptance=False,optimization_speedup_proven=False)
if data['status']=='MEASURED':
    if data['timing_eligible'] is not False or not data['boot_unchanged'] or not data['cmdline_unchanged'] or not data['cleanup']['buffers_released']:
        raise RuntimeError('Diagnostic/safety contract')
    record=data['diagnostic']['steps'][0];attribution=summarize(record)
    if attribution['counters']['logical_calls']!=162 or len(attribution['families'])!=154 or len(data['transactions'])!=attribution['counters']['host_calls']:
        raise RuntimeError('Wrong single-step coverage')
    if any(int(r['ap_return'])!=0x4D395832 for r in data['transactions']):raise RuntimeError('Physical Build identity')
    interpretation.update(read_io_summary(record['trace']['events']))
    interpretation.update(attribution=attribution,
        note='Language-only checkpoint replay; vision allocations absent. Counters process-wide, not exact per-file sectors. Capture still awaits same-quant reference.')
out=base/'gates/G01-decode-replay/attempt_01'
with exclusive_lock(base/'control.lock'):
    out.mkdir(parents=True,exist_ok=False);(out/'board_result.json').write_bytes(raw)
    write_json(out/'result.json',dict(status=data['status'],summary=summary,interpretation=interpretation,
        board_result_sha256=sha256(out/'board_result.json'),uart_sha256=sha256(logs/'run.log'),export_sha256=sha256(logs/'export.log')))
    path=root/'deployment/mage_vl4b/BOARD_GATE_RESULT.json';index=json.loads(path.read_text(encoding='utf-8-sig'))
    index['latest_decode_replay']=dict(status=data['status'],result=str((out/'result.json').relative_to(root)),sha256=sha256(out/'result.json'),numerical_acceptance=False)
    write_json(path,index)
    path=base/'STATE.json';state=json.loads(path.read_text());state['results']['decode_replay']=str((out/'result.json').relative_to(root))
    state['next_action']='Review actual replay terminal and read I/O attribution; collect captured layer0 gate_up tensors for same-quant reference before optimization. Do not infer speedup from changed memory/cache condition.'
    write_json(path,state)
print(json.dumps(dict(status=data['status'],outer_decode_s=data.get('outer_decode_s'),read_process_io=interpretation.get('read_process_io'),output_token=data.get('output_token'))))
