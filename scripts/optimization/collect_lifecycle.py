"""Collect raw terminal data without converting diagnostic success into a tier."""
import base64
import hashlib
import json
from pathlib import Path
import re
import zlib
from measurement import sha256,write_json,exclusive_lock
root=Path(__file__).resolve().parents[2];base=root/'deployment/mage_vl4b/optimization_v1'
logs=root/'tmp/op01_lifecycle01'
run=(logs/'run.log').read_text(encoding='utf-8-sig');text=(logs/'export.log').read_text(encoding='utf-8-sig')
if not re.search(r'__LIFECYCLE_RC_[01]__',run) or '__LIFECYCLE_EXPORT_RC_0__' not in text or 'LIFECYCLE_EXPORT_END' not in text:
    raise RuntimeError('Missing terminal proof')
summary=json.loads(run.split('REPLAY_JSON_BEGIN',1)[1].split('REPLAY_JSON_END',1)[0])
meta=json.loads(re.search(r'LIFECYCLE_EXPORT_META (.+)',text).group(1))
chunks=re.findall(r'LIFECYCLE_EXPORT_CHUNK (\d+) ([A-Za-z0-9+/=]+)',text)
if [int(i) for i,_ in chunks]!=list(range(len(chunks))):raise RuntimeError('Chunk sequence')
packed=base64.b64decode(''.join(v for _,v in chunks),validate=True)
if len(packed)!=meta['packed_bytes'] or hashlib.sha256(packed).hexdigest()!=meta['packed_sha256']:raise RuntimeError('Packed identity')
raw=zlib.decompress(packed)
if len(raw)!=meta['raw_bytes'] or hashlib.sha256(raw).hexdigest()!=meta['raw_sha256'] or meta['raw_sha256']!=summary['full_result_sha256']:raise RuntimeError('Raw identity')
data=json.loads(raw)
if data['package_manifest_sha256']!=sha256(base/'candidates/OP01-LIFECYCLE-01/PACKAGE_MANIFEST.json'):raise RuntimeError('Candidate identity')
out=base/'gates/G01-lifecycle/attempt_01'
with exclusive_lock(base/'control.lock'):
    if out.exists():raise RuntimeError('Immutable result exists')
    out.mkdir(parents=True)
    (out/'board_result.json').write_bytes(raw)
    write_json(out/'result.json',dict(status=data['status'],raw_sha256=meta['raw_sha256'],
        formal_performance_pass=False,requires_review=True,source_log_sha256=sha256(logs/'export.log')))
    p=root/'deployment/mage_vl4b/BOARD_GATE_RESULT.json';index=json.loads(p.read_text(encoding='utf-8-sig'))
    index['latest_lifecycle']=dict(status=data['status'],result=str((out/'result.json').relative_to(root)),sha256=sha256(out/'result.json'),performance_pass=False)
    write_json(p,index)
    p=base/'STATE.json';state=json.loads(p.read_text());state['results']['lifecycle']=str((out/'result.json').relative_to(root))
    state['next_action']='Review terminal lifecycle raw evidence and cleanup; validate per-state physical calls, KV/logits, timing and memory before any conclusion. No automatic rerun or tier promotion.'
    write_json(p,state)
print('LIFECYCLE_TERMINAL_COLLECTED_REVIEW_REQUIRED '+data['status'])
