"""Export existing immutable result only. Never construct a model or rerun gate."""
import base64
import hashlib
import json
import os
from pathlib import Path

def emit_saved():
    if os.geteuid()!=0:raise RuntimeError('Root export identity required')
    raw=Path('/home/ubuntu/m352_load_memory_evidence_01/load-memory.json').read_bytes()
    result=json.loads(raw)
    code=result['gate_return_code']
    if type(code) is not int or code not in (0,1):raise RuntimeError('Invalid saved rc')
    print('M352_RESULT_SHA256='+hashlib.sha256(raw).hexdigest(),flush=True)
    print('M352_SAVED_GATE_RC='+str(code),flush=True)
    parts=[raw[i:i+1800] for i in range(0,len(raw),1800)]
    for i,part in enumerate(parts):
        print('M352_RESULT_CHUNK='+str(i)+'/'+str(len(parts))+':'+base64.b64encode(part).decode('ascii'),flush=True)

if __name__=='__main__':emit_saved()
