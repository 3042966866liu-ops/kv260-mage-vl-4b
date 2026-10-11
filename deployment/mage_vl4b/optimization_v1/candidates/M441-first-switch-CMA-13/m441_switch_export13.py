"""Collect fresh diagnostic original bytes; never execute hardware."""
import base64
import hashlib
import json
from pathlib import Path
import time

OUT=Path('/home/ubuntu/m441_first_switch_cma_evidence_13')

def emit():
    p=OUT/'DIAG_RESULT.json'
    if not p.exists():
        # An unsafe retained gate may be collected while its original owner stays alive.
        raw=(OUT/'BOARD_RESULT.json').read_bytes()
        gate=json.loads(raw)
        value=dict(schema='m441-first-switch-cma13',status='FAIL_RETAINED_M441_CMA13',original_gate_rc=gate['gate_return_code'],original_owner_raw_sha256=hashlib.sha256(raw).hexdigest(),gate=gate,diagnostic=json.loads((OUT/'DIAGNOSTIC_PROGRESS.json').read_bytes()) if (OUT/'DIAGNOSTIC_PROGRESS.json').exists() else {})
        p.write_text(json.dumps(value,separators=(',',':'))+'\n',encoding='utf-8')
    raw=p.read_bytes()
    if len(raw)>2*1024*1024:raise RuntimeError('Diagnostic evidence exceeds fixed 2MiB bound')
    value=json.loads(raw)
    print('M441D_RESULT_SHA256='+hashlib.sha256(raw).hexdigest(),flush=True)
    print('M441D_ORIGINAL_GATE_RC='+str(value['original_gate_rc']),flush=True)
    parts=[raw[i:i+900] for i in range(0,len(raw),900)]
    for i,part in enumerate(parts):
        print('M441D_RESULT_CHUNK='+str(i)+'/'+str(len(parts))+':'+base64.b64encode(part).decode(),flush=True);time.sleep(.02)
    print('M441D_EXPORT_DONE',flush=True)

if __name__=='__main__':emit()
