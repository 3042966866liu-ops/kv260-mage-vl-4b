"""Prioritize the video actually selected on the page after a worker restart."""
from pathlib import Path
import hashlib,json,urllib.request
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[1]
out=ROOT/'deployment/mage_vl4b/optimization_v1/runs/M544-selected-input-UI-05';out.mkdir(exist_ok=False)
for name in ['static/playback_live.js','static/demo.html']:
 p=HERE/name;(out/('before_'+p.name)).open('xb').write(p.read_bytes())
p=HERE/'static/playback_live.js';s=p.read_text(encoding='utf-8')
old="v.pause();await seek(v,0);samples();phase='preparing';autoPlay=true";assert s.count(old)==1
s=s.replace(old,"await api('/api/input/select',{upload_id:upload.id});"+old)
old='samples();autoPlay=playWhenReady';assert s.count(old)==1
s=s.replace(old,"samples();await api('/api/input/select',{upload_id:upload.id});autoPlay=playWhenReady")
p.write_text(s,encoding='utf-8')
p=HERE/'static/demo.html';s=p.read_text(encoding='utf-8');assert '?v=alarm-no-seek09' in s;p.write_text(s.replace('?v=alarm-no-seek09','?v=selected-input05'),encoding='utf-8')
s=(HERE/'qa_alarm_no_seek09.cjs').read_text(encoding='utf-8').replace('qa/alarm_no_seek09','qa/input_selection05')
(HERE/'qa_input_selection05.cjs').open('x',encoding='utf-8').write(s)
s=(HERE/'run_alarm_no_seek09.py').read_text(encoding='utf-8').replace('qa/alarm_no_seek09','qa/input_selection05').replace('ui_alarm_no_seek09','ui_selected_input05').replace('qa_alarm_no_seek09.cjs','qa_input_selection05.cjs')
(HERE/'run_input_selection05.py').open('x',encoding='utf-8').write(s)
compile((HERE/'live_server.py').read_bytes(),'live_server.py','exec')
print('Selected input priority UI prepared; no board changes')
