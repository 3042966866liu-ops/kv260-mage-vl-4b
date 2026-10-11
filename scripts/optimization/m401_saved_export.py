"""Read exactly one saved failed result. No model/Overlay/gate imports."""
import base64
import hashlib
import json
import os
from pathlib import Path
import sys
import time
HERE=Path(__file__).resolve().parent
RESULT=Path('/home/ubuntu/m401_tail_text_01/B1/load-memory.json')
EXPECTED='9530a03974a7b330be21f39e07eaea1ef4c1eb53eacc86f89a155054994d9ca9'
def main():
    if len(sys.argv)!=3 or sys.argv[2]!='--collect-saved' or os.geteuid()!=0:raise RuntimeError('Explicit root saved-only collection required')
    manifest=HERE/'PACKAGE_MANIFEST.json'
    if hashlib.sha256(manifest.read_bytes()).hexdigest()!=sys.argv[1]:raise RuntimeError('Recovery package SHA differs')
    m=json.loads(manifest.read_bytes())
    if m['file_count']!=1 or [r['path'] for r in m['files']]!=['m401_saved_export.py'] or {p.name for p in HERE.iterdir()}!={'m401_saved_export.py','PACKAGE_MANIFEST.json'}:raise RuntimeError('Recovery whitelist differs')
    row=m['files'][0];p=HERE/row['path']
    if p.stat().st_size!=row['bytes'] or hashlib.sha256(p.read_bytes()).hexdigest()!=row['sha256'] or m['total_bytes']!=row['bytes']:raise RuntimeError('Recovery payload differs')
    before=RESULT.stat()
    if RESULT.is_symlink() or not 0<before.st_size<=1<<20:raise RuntimeError('Original result identity/size differs')
    raw=RESULT.read_bytes();after=RESULT.stat()
    if (before.st_dev,before.st_ino,before.st_size,before.st_mtime_ns,before.st_ctime_ns)!=(after.st_dev,after.st_ino,after.st_size,after.st_mtime_ns,after.st_ctime_ns):raise RuntimeError('Saved result changed')
    if hashlib.sha256(raw).hexdigest()!=EXPECTED:raise RuntimeError('Original failure SHA differs')
    r=json.loads(raw)
    if r['gate_return_code']!=1 or r['status']!='FAIL' or r['case']!='B1' or r['build_id']!='0x4D333537' or r['gate_level']!='sealed-DMA-fixed30-full36-layer-tail-prefill':raise RuntimeError('Wrong saved failure')
    if r['overlay_loaded'] or r['model_forward_calls'] or r['fpga_transactions'] or r['allocated_buffers'] or r['released_buffers'] or r['unsafe_buffers_retained']:raise RuntimeError('Pre-resource failure scope differs')
    print('M401_RECOVER_SHA256='+EXPECTED,flush=True)
    parts=[raw[i:i+900] for i in range(0,len(raw),900)]
    for i,piece in enumerate(parts):
        print(f'M401_RECOVER_CHUNK={i}/{len(parts)}:'+base64.b64encode(piece).decode('ascii'),flush=True);time.sleep(.005)
    print('M401_RECOVER_DONE original_gate_rc=1',flush=True)
if __name__=='__main__':main()
