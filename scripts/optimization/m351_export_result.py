"""Export existing saved bytes; never execute/repeat a component gate."""
import base64
import hashlib
import json
import os
from pathlib import Path

def main():
    if os.geteuid()!=0:raise RuntimeError('Root required for existing result')
    raw=Path('/home/ubuntu/m351_ps_component_evidence_01/BOARD_RESULT.json').read_bytes()
    r=json.loads(raw);code=r['gate_return_code']
    if type(code)is not int or code not in (0,1):raise RuntimeError('Invalid saved gate rc')
    print('M351_RESULT_SHA256='+hashlib.sha256(raw).hexdigest(),flush=True)
    print('M351_SAVED_GATE_RC='+str(code),flush=True)
    parts=[raw[i:i+1800] for i in range(0,len(raw),1800)]
    for i,part in enumerate(parts):print('M351_RESULT_CHUNK='+str(i)+'/'+str(len(parts))+':'+base64.b64encode(part).decode('ascii'),flush=True)

if __name__=='__main__':main()
