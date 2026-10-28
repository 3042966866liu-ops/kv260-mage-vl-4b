"""Preserve previous UI, remove alarm rewind and create isolated regression."""
from pathlib import Path
import hashlib,json
HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]
out=ROOT/'deployment/mage_vl4b/optimization_v1/runs/M544-alarm-no-seek-UI-09'
out.mkdir(exist_ok=False)
sources=['static/playback_live.js','static/demo.html']
before={}
for name in sources:
    p=HERE/name
    data=p.read_bytes();before[name]=hashlib.sha256(data).hexdigest()
    (out/('before_'+p.name)).write_bytes(data)
p=HERE/sources[0];s=p.read_text(encoding='utf-8')
old="v.pause();v.loop=false;v.currentTime=upload.cases[0].timestamp_ms/1000"
assert s.count(old)==1
s=s.replace(old,"v.pause();v.loop=false;/* Alarm preserves playback position; evidence stays in the sample panel. */")
p.write_text(s,encoding='utf-8')
p=HERE/sources[1];s=p.read_text(encoding='utf-8');assert '?v=preparation06' in s
p.write_text(s.replace('?v=preparation06','?v=alarm-no-seek09'),encoding='utf-8')
s=(HERE/'qa_preparation08.cjs').read_text(encoding='utf-8')
s=s.replace('qa/preparation_software08','qa/alarm_no_seek09')
old="active.decision='Yes';active.status='review';"
assert s.count(old)==1
s=s.replace(old,"""await page.locator('#video-player').evaluate(v=>{v.pause();v.currentTime=5.5});
  for(let i=0;i<40;i++){if(await page.locator('#video-player').evaluate(v=>!v.seeking&&Math.abs(v.currentTime-5.5)<.05))break;await page.waitForTimeout(50)}
  const alarmPosition=await page.locator('#video-player').evaluate(v=>v.currentTime);assert(Math.abs(alarmPosition-5.5)<.05);
  const sampleTime=(await (await page.request.get(base+'/api/uploads/'+active.upload_id)).json()).cases[0].timestamp_ms/1000;
  assert(Math.abs(sampleTime-alarmPosition)>1,'fixture must distinguish playback from sampled frame');
  active.decision='Yes';active.status='review';""")
old="assert(await page.locator('#alarm-history').isVisible());"
assert s.count(old)==1
s=s.replace(old,old+"await page.waitForTimeout(300);assert(Math.abs((await page.locator('#video-player').evaluate(v=>v.currentTime))-alarmPosition)<.05,'alarm must not seek to sampled evidence');")
s=s.replace("'Yes huge alert and frame pause'","'Yes huge alert and current-position pause without seeking to sample'")
(HERE/'qa_alarm_no_seek09.cjs').write_text(s,encoding='utf-8')
s=(HERE/'run_ui_reselect08.py').read_text(encoding='utf-8').replace('qa/preparation_software08','qa/alarm_no_seek09').replace('ui_wait08','ui_alarm_no_seek09').replace('qa_preparation08.cjs','qa_alarm_no_seek09.cjs')
(HERE/'run_alarm_no_seek09.py').write_text(s,encoding='utf-8')
(out/'PREPARATION.json').write_text(json.dumps(dict(before=before,root_cause=old,board_commands=0,model_runs=0),indent=2),encoding='utf-8')
print('UI patch and isolated regression prepared',out)
