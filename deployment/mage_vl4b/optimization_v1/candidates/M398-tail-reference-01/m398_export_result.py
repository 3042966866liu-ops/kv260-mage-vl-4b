"""Export saved bytes only, independent of probe imports."""
import base64
import hashlib
import json
import os
from pathlib import Path
import sys
import time

def emit_saved(case):
    if os.geteuid()!=0 or case not in ('A1','B1','B2','A2'):raise RuntimeError('Root/known case required')
    raw=(Path('/home/ubuntu/m398_tail_reference_01')/case/'load-memory.json').read_bytes();r=json.loads(raw)
    assert r['case']==case and r['gate_level']=='sealed-DMA-original-fixed159-tail-reference'
    print('M398_RESULT_SHA256='+hashlib.sha256(raw).hexdigest(),flush=True)
    print('M398_SAVED_GATE_RC='+str(r['gate_return_code']),flush=True)
    chunks=[raw[i:i+900] for i in range(0,len(raw),900)]
    for i,p in enumerate(chunks):
        print(f'M398_RESULT_CHUNK={i}/{len(chunks)}:'+base64.b64encode(p).decode('ascii'),flush=True)
        time.sleep(0.04)

if __name__=='__main__':emit_saved(sys.argv[1])
