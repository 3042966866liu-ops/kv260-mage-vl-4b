import base64
import hashlib
import json
from pathlib import Path
import re
import zlib
import numpy as np
from measurement import exclusive_lock,sha256,write_json

ROOT=Path(__file__).resolve().parents[2]
BASE=ROOT/'deployment/mage_vl4b/optimization_v1'
log=ROOT/'tmp/op01_input_reference01/run.log'
text=log.read_text(encoding='utf-8-sig')
if '__OP01_RGB_RC_0__' not in text or 'OP01_RGB_EXPORT_END' not in text:
    raise RuntimeError('No completed input export')
metadata=json.loads(text.split('OP01_RGB_METADATA_BEGIN',1)[1].split('OP01_RGB_METADATA_END',1)[0])
chunks=re.findall(r'OP01_RGB_CHUNK (\d+) ([A-Za-z0-9+/=]+)',text)
if [int(x[0]) for x in chunks]!=list(range(len(chunks))):raise RuntimeError('Chunk gap/order error')
compressed=base64.b64decode(''.join(x[1] for x in chunks),validate=True)
if hashlib.sha256(compressed).hexdigest()!=metadata['compressed_sha256']:raise RuntimeError('Compressed SHA mismatch')
payload=zlib.decompress(compressed)
if len(payload)!=metadata['raw_bytes'] or hashlib.sha256(payload).hexdigest()!=metadata['raw_sha256']:
    raise RuntimeError('Raw RGB identity mismatch')
frames=np.frombuffer(payload,np.uint8).reshape(metadata['shape'])
with exclusive_lock(BASE/'control.lock'):
    output=BASE/'datasets/dev_bootstrap_v1/board_reference_v1'
    output.mkdir(exist_ok=False)
    np.save(output/'dev-0001_rgb.npy',frames,allow_pickle=False)
    result=dict(status='PASS',scope='Identical board RGB bound to software reference only; SYS must decode raw again',
        metadata=metadata,rgb_file_sha256=sha256(output/'dev-0001_rgb.npy'),
        uart_evidence=dict(path=str(log),sha256=sha256(log)),model_inference=False)
    write_json(output/'result.json',result)
    gate=BASE/'gates/G01-input-binding/attempt_01/result.json'
    write_json(gate,result)
    index_path=ROOT/'deployment/mage_vl4b/BOARD_GATE_RESULT.json'
    index=json.loads(index_path.read_text(encoding='utf-8-sig'))
    index['latest_optimization_v1_input_binding']=dict(status='PASS',result=str(gate.relative_to(ROOT)),
        sha256=sha256(gate),rgb_sha256=metadata['raw_sha256'],model_inference=False)
    write_json(index_path,index)
    state_path=BASE/'STATE.json';state=json.loads(state_path.read_text())
    state['results']['board_input_binding']=str(gate)
    state['next_action']='Run full4frame software reference from board RGB, then causal SYS board gate'
    write_json(state_path,state)
print(json.dumps(dict(status='PASS',reference=str(output/'dev-0001_rgb.npy'),compressed_bytes=len(compressed))))
