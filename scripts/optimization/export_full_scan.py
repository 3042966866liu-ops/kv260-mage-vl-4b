import base64
import hashlib
import json
from pathlib import Path
import sys
import zlib
if hashlib.sha256(Path(__file__).read_bytes()).hexdigest()!=sys.argv[1]:raise RuntimeError('Exporter identity')
path=Path('/home/ubuntu/op01_full_file_scan_01/result.json')
if not 0<path.stat().st_size<=4*1024*1024:raise RuntimeError('Export bound')
raw=path.read_bytes()
if hashlib.sha256(raw).hexdigest()!=sys.argv[2]:raise RuntimeError('Result identity')
packed=zlib.compress(raw,9)
print('SCAN_EXPORT_META '+json.dumps(dict(raw_sha256=hashlib.sha256(raw).hexdigest(),raw_bytes=len(raw),packed_sha256=hashlib.sha256(packed).hexdigest(),packed_bytes=len(packed))))
encoded=base64.b64encode(packed).decode()
for i in range(0,len(encoded),1600):print(f'SCAN_EXPORT_CHUNK {i//1600} '+encoded[i:i+1600],flush=True)
print('SCAN_EXPORT_END',flush=True)
