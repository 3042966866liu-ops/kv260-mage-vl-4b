"""Export original complete-MLP diagnostic bytes only."""
import base64,hashlib,json,os,time
from pathlib import Path
OUTPUT=Path('/home/ubuntu/m414_layer12_full_visual_01/BOARD_RESULT.json')
def emit_saved():
    if os.geteuid()!=0:raise RuntimeError('Root saved-only export required')
    raw=OUTPUT.read_bytes();r=json.loads(raw)
    if not 0<len(raw)<=512<<10 or r['gate_level']!='layer12-full-visual-feature-quality' or r['gate_return_code'] not in (0,1):raise RuntimeError('Saved export identity/budget differs')
    parts=[raw[i:i+900] for i in range(0,len(raw),900)]
    print('M414_RESULT_SHA256='+hashlib.sha256(raw).hexdigest(),flush=True);print('M414_SAVED_GATE_RC='+str(r['gate_return_code']),flush=True)
    for i,p in enumerate(parts):print(f'M414_RESULT_CHUNK={i}/{len(parts)}:'+base64.b64encode(p).decode('ascii'),flush=True);time.sleep(.16)
if __name__=='__main__':emit_saved()
