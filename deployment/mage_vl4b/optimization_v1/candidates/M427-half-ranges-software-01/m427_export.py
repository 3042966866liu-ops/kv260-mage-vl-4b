"""Export original immutable CPU-only result, never execute a model."""
import base64,hashlib,json,os,time
from pathlib import Path
OUTPUT=Path('/home/ubuntu/m427_half_ranges_software_01/BOARD_RESULT.json')
def emit_saved():
    if os.geteuid()!=0:raise RuntimeError('Root export required')
    raw=OUTPUT.read_bytes();r=json.loads(raw)
    if not 0<len(raw)<=2<<20 or r['gate_level']!='CPU-only-cumulative-visual-MLP-range-screen' or type(r['gate_return_code']) is not int or r['gate_return_code'] not in (0,1):raise RuntimeError('Saved identity/budget differs')
    parts=[raw[i:i+900] for i in range(0,len(raw),900)]
    print('M427_RESULT_SHA256='+hashlib.sha256(raw).hexdigest(),flush=True);print('M427_SAVED_GATE_RC='+str(r['gate_return_code']),flush=True)
    for i,p in enumerate(parts):print(f'M427_RESULT_CHUNK={i}/{len(parts)}:'+base64.b64encode(p).decode('ascii'),flush=True);time.sleep(.16)
if __name__=='__main__':emit_saved()
