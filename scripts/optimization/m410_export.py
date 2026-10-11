"""Root export of saved bytes only; no PYNQ/model imports or execution."""
import argparse,base64,hashlib,json,os,time
from pathlib import Path
EVIDENCE=Path('/home/ubuntu/m410_visual_linear_01')
def emit_saved(mode):
    if os.geteuid()!=0:raise RuntimeError('Root saved export required')
    p=EVIDENCE/mode/'BOARD_RESULT.json';raw=p.read_bytes()
    if not 0<len(raw)<=256<<10:raise RuntimeError('Saved result bound exceeded')
    r=json.loads(raw)
    if r['gate_level']!=mode or type(r['gate_return_code']) is not int or r['gate_return_code'] not in (0,1):raise RuntimeError('Saved identity/rc differs')
    parts=[raw[i:i+900] for i in range(0,len(raw),900)]
    print('M410_RESULT_SHA256='+hashlib.sha256(raw).hexdigest(),flush=True)
    print('M410_SAVED_GATE_RC='+str(r['gate_return_code']),flush=True)
    for i,part in enumerate(parts):
        print(f'M410_RESULT_CHUNK={i}/{len(parts)}:'+base64.b64encode(part).decode('ascii'),flush=True);time.sleep(.16)
    return len(parts)
if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('mode',choices=('Descriptor','Chain'));a=ap.parse_args();emit_saved(a.mode)
