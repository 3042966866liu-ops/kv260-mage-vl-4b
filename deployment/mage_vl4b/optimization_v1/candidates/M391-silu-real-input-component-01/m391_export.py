"""Export saved original CPU component bytes only."""
import base64
import hashlib
import json
import os
from pathlib import Path
import time

def main():
    if os.geteuid()!=0:raise RuntimeError('Root required')
    raw=Path('/home/ubuntu/m391_silu_component_01/RESULT.json').read_bytes();r=json.loads(raw)
    assert r['gate_level']=='CPU-only-real159-SiLU-workspace'
    print('M391_RESULT_SHA256='+hashlib.sha256(raw).hexdigest(),flush=True)
    print('M391_SAVED_GATE_RC='+str(r['gate_return_code']),flush=True)
    parts=[raw[i:i+900] for i in range(0,len(raw),900)]
    for i,p in enumerate(parts):
        print(f'M391_RESULT_CHUNK={i}/{len(parts)}:'+base64.b64encode(p).decode('ascii'),flush=True);time.sleep(.04)

if __name__=='__main__':main()
