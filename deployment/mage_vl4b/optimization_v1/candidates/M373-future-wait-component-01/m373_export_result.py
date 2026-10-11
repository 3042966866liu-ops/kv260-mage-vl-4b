"""Read-only recovery of saved raw evidence; no gate import or re-execution."""
import base64
import hashlib
import json
import os
from pathlib import Path
import time

def main():
    if os.geteuid() != 0: raise RuntimeError('Root required')
    raw = Path('/home/ubuntu/m373_future_wait_evidence_01/BOARD_RESULT.json').read_bytes()
    code = json.loads(raw)['gate_return_code']
    if type(code) is not int or code not in (0, 1): raise RuntimeError('Invalid saved rc')
    print('M373_RESULT_SHA256='+hashlib.sha256(raw).hexdigest(), flush=True)
    print('M373_SAVED_GATE_RC='+str(code), flush=True)
    parts = [raw[i:i+900] for i in range(0,len(raw),900)]
    for i, part in enumerate(parts):
        print('M373_RESULT_CHUNK='+str(i)+'/'+str(len(parts))+':'+base64.b64encode(part).decode('ascii'), flush=True)
        time.sleep(0.04)

if __name__ == '__main__': main()
