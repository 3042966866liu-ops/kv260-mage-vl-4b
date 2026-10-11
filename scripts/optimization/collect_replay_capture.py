import base64
import hashlib
import io
import json
from pathlib import Path
import re
import zlib
import numpy as np
from measurement import sha256,write_json,exclusive_lock
root=Path(__file__).resolve().parents[2];base=root/'deployment/mage_vl4b/optimization_v1'
log=root/'tmp/op01_replay_capture01/run.log';text=log.read_text(encoding='utf-8-sig')
if '__CAPTURE_RC_0__' not in text or 'CAPTURE_END' not in text:raise RuntimeError('Incomplete capture transfer')
meta=json.loads(re.search(r'CAPTURE_META (.+)',text).group(1));chunks=re.findall(r'CAPTURE_CHUNK (\d+) ([A-Za-z0-9+/=]+)',text)
if [int(i) for i,v in chunks]!=list(range(len(chunks))):raise RuntimeError('Chunk order')
packed=base64.b64decode(''.join(v for i,v in chunks),validate=True)
if len(packed)!=meta['packed_bytes'] or hashlib.sha256(packed).hexdigest()!=meta['packed_sha256']:raise RuntimeError('Packed identity')
raw=zlib.decompress(packed)
if len(raw)!=meta['raw_bytes'] or hashlib.sha256(raw).hexdigest()!=meta['raw_sha256']:raise RuntimeError('Raw identity')
files={k:base64.b64decode(v,validate=True) for k,v in json.loads(raw).items()}
board_path=base/'gates/G01-decode-replay/attempt_01/board_result.json';board=json.loads(board_path.read_text())
if set(files)!={'manifest.json','array00.npy','array01.npy','array02.npy','array03.npy'}:raise RuntimeError('Whitelist')
if hashlib.sha256(files['manifest.json']).hexdigest()!=board['capture_manifest_sha256']:raise RuntimeError('Manifest identity')
manifest=json.loads(files['manifest.json'])
if manifest['files']!=board['captures']:raise RuntimeError('Board capture identity')
for row in manifest['files']:
    data=files[row['file']]
    if hashlib.sha256(data).hexdigest()!=row['sha256']:raise RuntimeError('Member identity')
    array=np.load(io.BytesIO(data),allow_pickle=False)
    if list(array.shape)!=row['shape'] or str(array.dtype)!=row['dtype'] or not np.isfinite(array).all():raise RuntimeError('Numeric payload identity')
out=base/'runs/OP01-replay01-real-capture'
with exclusive_lock(base/'control.lock'):
    out.mkdir(exist_ok=False)
    for name,data in files.items():(out/name).write_bytes(data)
    write_json(out/'TRANSFER_RESULT.json',dict(status='CAPTURE_VERIFIED',board_source_sha256=sha256(board_path),
        uart_sha256=sha256(log),manifest_sha256=sha256(out/'manifest.json'),numerical_acceptance=False))
print('REAL_CAPTURE_TRANSFER_VERIFIED '+str(out))
