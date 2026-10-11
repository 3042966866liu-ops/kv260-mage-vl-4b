"""Export only existing capacity bytes; never import or execute the probe."""
import base64
import hashlib
import json
import os
from pathlib import Path

def emit_saved():
    if os.geteuid()!=0:raise RuntimeError('Root required')
    path=Path('/home/ubuntu/m358_candidate_capacity_01/load-memory.json')
    raw=path.read_bytes();r=json.loads(raw)
    assert r['gate_level']=='load-only-memory-diagnostic' and r['build_id']=='0x4D333537'
    print('M358_RESULT_SHA256='+hashlib.sha256(raw).hexdigest(),flush=True)
    print('M358_SAVED_GATE_RC='+str(r['gate_return_code']),flush=True)
    chunks=[raw[i:i+900] for i in range(0,len(raw),900)]
    for i,p in enumerate(chunks):print(f'M358_RESULT_CHUNK={i}/{len(chunks)}:'+base64.b64encode(p).decode('ascii'),flush=True)

if __name__=='__main__':emit_saved()
