import base64,hashlib,json,os
from pathlib import Path
if os.geteuid()!=0:raise RuntimeError('Root required')
raw=Path('/home/ubuntu/m368_identity_preflight_01/RESULT.json').read_bytes();r=json.loads(raw)
print('M368_IDENTITY_SHA256='+hashlib.sha256(raw).hexdigest(),flush=True)
print('M368_IDENTITY_RC='+str(r['gate_return_code']),flush=True)
parts=[raw[i:i+900] for i in range(0,len(raw),900)]
for i,p in enumerate(parts):print(f'M368_IDENTITY_CHUNK={i}/{len(parts)}:'+base64.b64encode(p).decode(),flush=True)
