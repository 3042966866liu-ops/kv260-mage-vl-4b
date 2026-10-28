"""Bind only after actual new-boot Import; verify old-upload priority without FPGA."""
from pathlib import Path
import hashlib,json,sys,urllib.request
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[1];RUNS=ROOT/'deployment/mage_vl4b/optimization_v1/runs'
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
read=lambda p:json.loads(Path(p).read_bytes())
with urllib.request.urlopen('http://127.0.0.1:8766/api/state',timeout=4) as r:state=json.load(r)
assert state['worker'] is None,'Do not restart an active worker'
prep=RUNS/'M544-campus-live-worker-preparation-05/RESULT.json';p=read(prep);imported=RUNS/'M544-campus-live-worker-board-05/Import/BOARD_RESULT.json';v=read(imported)
assert v['primary_rc']==0 and v['package_manifest_sha256']==p['manifest_sha256'] and v['CPU_components']['live_frame_protocol']['negative_cases']==13
qa=HERE/'qa/input_selection05/RESULT.json';q=read(qa);assert q['FPGA_runs']==0 and q['fake_predictions'] and len(q['checks'])==13
sys.path.insert(0,str(HERE));from live_server import LiveStore
s=LiveStore(HERE/'var/ui_selected_input05/events.sqlite')
with s.db() as c:ids=[r['id'] for r in c.execute('SELECT id FROM uploads ORDER BY created')]
assert len(ids)==2
s.worker=dict(session='a'*32,ready=True)
assert s.prepare_next()['frame']['upload_id']==ids[-1]
s.select_input(dict(upload_id=ids[0]));assert s.prepare_next()['frame']['upload_id']==ids[0]
for invalid in [{'upload_id':'bad'},{'upload_id':'0'*32},{'upload_id':ids[0],'expected_decision':'Yes'}]:
 try:s.select_input(invalid)
 except ValueError:pass
 else:raise AssertionError('Invalid selection accepted')
with s.db() as c:c.execute("INSERT INTO events(id,kind,case_id,status,created,updated) VALUES('busy-test','live','fixture','running',0,0)")
try:
 try:s.select_input(dict(upload_id=ids[1]))
 except ValueError:pass
 else:raise AssertionError('Busy input switch accepted')
finally:
 with s.db() as c:c.execute("DELETE FROM events WHERE id='busy-test'")
out=RUNS/'M544-live-binding-current-boot-05';out.mkdir(exist_ok=False);f=HERE/'LIVE_BINDING.json';(out/'LIVE_BINDING_before05.json').open('xb').write(f.read_bytes())
b=read(f);b.update(package_manifest_sha256=p['manifest_sha256'],worker_preparation=prep.relative_to(ROOT).as_posix(),worker_import_result=imported.relative_to(ROOT).as_posix(),worker_expected_boot=p['expected_boot'])
temp=f.with_suffix('.binding05-partial');temp.open('x',encoding='utf-8').write(json.dumps(b,ensure_ascii=False,indent=2)+'\n');temp.replace(f)
result=dict(status='BOUND_M544_CURRENT_BOOT05_AFTER_A53_IMPORT',primary_rc=0,boot_id=p['expected_boot'],package_manifest_sha256=p['manifest_sha256'],preparation_sha256=sha(prep),Import_sha256=sha(imported),binding_sha256=sha(f),priority_checks=['fallback latest','explicit older selected upload wins','malformed id rejected','unknown id rejected','answer field rejected','busy selection rejected'],browser_fixture_SHA=sha(qa),browser_checks=13,models=0,board_commands=0,current_live_worker=False,server_restart_required=True,source={n:sha(HERE/n) for n in ['live_server.py','static/playback_live.js','static/demo.html']})
f=out/'RESULT.json';f.open('x',encoding='utf-8').write(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
sys.path.insert(0,str(ROOT/'scripts/optimization'));from m455456_workflow02 import synchronized
synchronized('latest_m544_binding05',dict(status=result['status'],result=f.relative_to(ROOT).as_posix(),sha256=sha(f),board=False,hardware=False,promoted=False),'## M544新boot实际A53 Import后网页绑定05\n\nRESULT SHA '+sha(f)+'；新工作器Install/Import原rc0、实际数据协议13拒绝/数学组件已核，绑定boot '+p['expected_boot']+'；尚未启动完整推理。发现旧链接恢复视频时只准备最新上传会遗漏所选旧视频，新增显式输入选择队列，仅选择真实已保存RGB、不含答案；六项选择组件及独立浏览器13项通过，0板/模型。待重启已确认自有本地服务并启动唯一工作器，旧证据与稳定回滚保持。')
print(result['status'],p['manifest_sha256'])
