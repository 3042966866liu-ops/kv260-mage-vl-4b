import base64,hashlib,json,os
from pathlib import Path
if os.geteuid()!=0:raise RuntimeError('Root required')
raw=Path('/home/ubuntu/m367_visual_reference_01/RESULT.json').read_bytes();r=json.loads(raw)
if r['gate_level']!='missing-PS-visual-reference-only':raise RuntimeError('Scope differs')
print('M367_RESULT_SHA256='+hashlib.sha256(raw).hexdigest(),flush=True)
print('M367_SAVED_GATE_RC='+str(r['gate_return_code']),flush=True)
chunks=[raw[i:i+900] for i in range(0,len(raw),900)]
for i,p in enumerate(chunks):print(f'M367_RESULT_CHUNK={i}/{len(chunks)}:'+base64.b64encode(p).decode('ascii'),flush=True)
