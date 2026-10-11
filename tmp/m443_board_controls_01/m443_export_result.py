"""Root-only export of saved original bytes; never launches a gate."""
import argparse
import base64
import hashlib
import json
import os
from pathlib import Path

EVIDENCE=Path('/home/ubuntu/m443_board_evidence_01')
MODES=('BuildID','Descriptor','Chain')

def emit_saved(mode):
    if mode not in MODES or os.geteuid()!=0:raise RuntimeError('Known mode/root required')
    path=EVIDENCE/mode/'BOARD_RESULT.json'
    raw=path.read_bytes();result=json.loads(raw)
    if result['gate_level']!=mode or result['build_id']!='0x4D343433':raise RuntimeError('Saved gate identity differs')
    rc=result['gate_return_code']
    if type(rc) is not int or rc not in (0,1):raise RuntimeError('Saved gate rc invalid')
    parts=[raw[i:i+900] for i in range(0,len(raw),900)]
    print('M443_RESULT_SHA256='+hashlib.sha256(raw).hexdigest(),flush=True)
    print('M443_SAVED_GATE_RC='+str(rc),flush=True)
    for i,part in enumerate(parts):
        print('M443_RESULT_CHUNK='+str(i)+'/'+str(len(parts))+':'+base64.b64encode(part).decode('ascii'),flush=True)
    return rc

if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('mode',choices=MODES);args=ap.parse_args();emit_saved(args.mode)
