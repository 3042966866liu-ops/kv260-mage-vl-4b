"""Bounded, saved-only original byte export."""
import base64,hashlib,json,os,time
from pathlib import Path
OUTPUT=Path('/home/ubuntu/m428_saved_feature_language_01/BOARD_RESULT.json')
def emit_saved():
    if os.geteuid()!=0:raise RuntimeError('Root export required')
    raw=OUTPUT.read_bytes();r=json.loads(raw)
    if not 0<len(raw)<=4<<20 or r['gate_level']!='saved-feature-fixed159-language-quality' or r['gate_return_code'] not in (0,1):raise RuntimeError('Saved identity/budget differs')
    parts=[raw[i:i+900] for i in range(0,len(raw),900)]
    print('M428_RESULT_SHA256='+hashlib.sha256(raw).hexdigest(),flush=True);print('M428_SAVED_GATE_RC='+str(r['gate_return_code']),flush=True)
    for i,p in enumerate(parts):print(f'M428_RESULT_CHUNK={i}/{len(parts)}:'+base64.b64encode(p).decode('ascii'),flush=True);time.sleep(.16)
if __name__=='__main__':emit_saved()
