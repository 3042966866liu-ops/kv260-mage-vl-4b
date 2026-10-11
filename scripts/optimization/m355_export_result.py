"""Existing raw bytes only; no hardware access or gate execution."""
import base64
import hashlib
import json
import os
from pathlib import Path


def emit_saved():
    if os.geteuid()!=0:raise RuntimeError('Root export identity required')
    raw=Path('/home/ubuntu/m355_device_phase_evidence_01/device-phase.json').read_bytes()
    code=json.loads(raw)['gate_return_code']
    if type(code) is not int or code not in (0,1):raise RuntimeError('Saved return code invalid')
    print('M355_RESULT_SHA256='+hashlib.sha256(raw).hexdigest(),flush=True)
    print('M355_SAVED_GATE_RC='+str(code),flush=True)
    parts=[raw[i:i+1800] for i in range(0,len(raw),1800)]
    for i,part in enumerate(parts):print('M355_RESULT_CHUNK='+str(i)+'/'+str(len(parts))+':'+base64.b64encode(part).decode('ascii'),flush=True)


if __name__=='__main__':emit_saved()
