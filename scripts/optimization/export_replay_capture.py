import base64
import hashlib
import json
from pathlib import Path
import sys
import zlib
def digest(data):return hashlib.sha256(data).hexdigest()
if digest(Path(__file__).read_bytes())!=sys.argv[1]:raise RuntimeError('Exporter identity')
root=Path('/home/ubuntu/op01_replay01.captures');raw_manifest=(root/'manifest.json').read_bytes()
if digest(raw_manifest)!=sys.argv[2]:raise RuntimeError('Capture manifest identity')
manifest=json.loads(raw_manifest)
if [r['file'] for r in manifest['files']]!=['array00.npy','array01.npy','array02.npy','array03.npy']:raise RuntimeError('Whitelist')
files={'manifest.json':base64.b64encode(raw_manifest).decode()}
for row in manifest['files']:
    path=root/row['file']
    if path.is_symlink() or not 0<path.stat().st_size<1024*1024:raise RuntimeError('Capture bound')
    data=path.read_bytes()
    if digest(data)!=row['sha256']:raise RuntimeError('Capture member hash')
    files[path.name]=base64.b64encode(data).decode()
raw=json.dumps(files,separators=(',',':')).encode();packed=zlib.compress(raw,9)
print('CAPTURE_META '+json.dumps(dict(raw_sha256=digest(raw),packed_sha256=digest(packed),raw_bytes=len(raw),packed_bytes=len(packed))))
encoded=base64.b64encode(packed).decode()
for i in range(0,len(encoded),1600):print(f'CAPTURE_CHUNK {i//1600} '+encoded[i:i+1600],flush=True)
print('CAPTURE_END',flush=True)
