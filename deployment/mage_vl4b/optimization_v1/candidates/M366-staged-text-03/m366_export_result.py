"""Export saved bytes only, independent of probe imports."""
import base64
import hashlib
import json
import os
from pathlib import Path
import sys

def emit_saved(case):
    if os.geteuid()!=0 or case not in ('A1','B1','B2','A2'):raise RuntimeError('Root/known case required')
    raw=(Path('/home/ubuntu/m366_staged_text_02')/case/'load-memory.json').read_bytes();r=json.loads(raw)
    assert r['case']==case and r['gate_level']=='independent-fixed-text-capacity-diagnostic'
    print('M366_RESULT_SHA256='+hashlib.sha256(raw).hexdigest(),flush=True)
    print('M366_SAVED_GATE_RC='+str(r['gate_return_code']),flush=True)
    chunks=[raw[i:i+900] for i in range(0,len(raw),900)]
    for i,p in enumerate(chunks):print(f'M366_RESULT_CHUNK={i}/{len(chunks)}:'+base64.b64encode(p).decode('ascii'),flush=True)

if __name__=='__main__':emit_saved(sys.argv[1])
