"""Saved original proof only; do not rerun a request to repair a checker."""
from pathlib import Path
import hashlib,json,sys,urllib.request
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[1];RUNS=ROOT/'deployment/mage_vl4b/optimization_v1/runs'
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
read=lambda p:json.loads(Path(p).read_bytes())
session='3a5b6c71e8c6454ea2ca3688ebebdb66';upload='3c26abf6c51141af809d824cb7c868e7';out=RUNS/'M544-six-hour-demo-restored-07'
assert (out/'actual_alarm.png').is_file()
with urllib.request.urlopen('http://127.0.0.1:8766/api/state',timeout=4) as r:state=json.load(r)
assert state['worker'] and state['worker']['session']==session and state['worker']['warm']
events=[e for e in state['events'] if e.get('upload_id')==upload and e.get('decision')=='Yes' and (RUNS/'M544-live-board-results'/session/e['id']/'RESULT.json').exists()]
assert len(events)==1
e=events[0];proof=RUNS/'M544-live-board-results'/session/e['id']/'RESULT.json';v=read(proof);binding=read(HERE/'LIVE_BINDING.json');prep=read(ROOT/binding['worker_preparation']);pkg=ROOT/prep['package'];plan=read(pkg/'DEMO_BOARD_PLAN.json')
assert prep['manifest_sha256']==v['package_manifest_sha256']==binding['package_manifest_sha256']=='251160c48069770fdfb649a59ac5826b186e30e5f1405ec3eb9a2bb51f4e01d9'
assert plan['persistent_worker']['idle_seconds']==plan['persistent_worker']['absolute_session_seconds']==21600 and plan['persistent_worker']['host_timeout_seconds']==22800
assert plan['persistent_worker']['max_live_jobs']==12
assert v['primary_rc']==0 and v['completed_request'] and v['argmax_verified'] and v['actual_full_vocab']==151936 and v['decision']=='Yes' and v['physical_calls']>=324
assert v['frame_sha256']=='1d8c3b1fe46320f44891618b83e9dab03d2c2d29a607d3cfd14d53820d44e6b1' and v['case_id']=='u'+upload+'_f0'
fixed=RUNS/'M544-live-fixed-gates'/session/'RESULT.json';a=read(fixed);assert a['primary_rc']==0 and a['answer_correct'] and a['boot_id']==plan['expected_boot']
cpu=RUNS/'M544-live-worker-CPU-07/RESULT.json';assert read(cpu)['protocol']['session_lifetime']['six_hour_absolute_bound']
arm=RUNS/'M544-campus-live-worker-board-07/Import/BOARD_RESULT.json';assert read(arm)['CPU_components']['live_frame_protocol']['session_lifetime']['expiry_returns_normally']
obs=read(out/'BROWSER_OBSERVATION.json');assert obs['alarm_visible'] and obs['video_paused'] and obs['no_latency_text']
r=dict(status='PASS_REAL_VIDEO07_ALARM_WITH_BOUNDED_SIX_HOUR_DEMO_SESSION',primary_rc=0,session=session,job=e['id'],boot_id=plan['expected_boot'],TTFT_s=v['TTFT_s'],decision=v['decision'],proof_path=proof.relative_to(ROOT).as_posix(),proof_sha256=sha(proof),fixed_warmup_sha256=sha(fixed),screenshot_sha256=sha(out/'actual_alarm.png'),idle_seconds=21600,absolute_acceptance_window_seconds=21600,host_timeout_seconds=22800,max_live_jobs=12,full_six_hour_soak_not_performed=True,CPU_lifetime_sha256=sha(cpu),A53_Import_sha256=sha(arm),disconnected_render_sha256=sha(RUNS/'M544-disconnected-status-UI-06/RESULT.json'),model_math_and_weights_unchanged=True,model_runs_in_audit=0,worker_still_live=True,seven_owners_intentionally_live=True,stable_restoration_not_claimed=True,only_selected_frame_not_whole_video=True,source={p:sha(HERE/p) for p in ['static/playback_live.js','live_uart07.ps1','run_live_worker07.py','start_demo.ps1']})
f=out/'RESULT.json';f.open('x',encoding='utf-8').write(json.dumps(r,ensure_ascii=False,indent=2)+'\n')
(out/'REPORT.md').open('x',encoding='utf-8').write('# 演示连接与等待提示修复\n\n原05会话20分钟空闲后正常退出，原host/native0、七owner逆序释放和稳定四clock闭合，原视频7的28.02963086秒Yes保持。此前网页把断开误报为传图，现已明确区分断开/初始化/实际传图。\n\n07会话空闲及停止接新任务窗口21600秒，主机22800秒留加载/收尾余量，最多12个新任务不变。实际协议CPU/A53过期边界均通过，未完成6小时连续运行实测；不是无限运行承诺。原Import06旧报告路径冲突0模型FAIL保留，07只隔离该组件报告。数学/权重不变。\n\n本次新会话一次固定预热后，一次视频7真实采样请求返回Yes，原用户页红色警示可见；完整词表/输入/新nonce/SHA绑定，不复用旧结果。工作器有意继续运行，不称owner已释放/稳定已恢复或全片识别。\n\nRESULT SHA '+sha(f)+'\n')
sys.path.insert(0,str(ROOT/'scripts/optimization'));from m455456_workflow02 import synchronized
synchronized('latest_m544_six_hour_demo07',dict(status=r['status'],result=f.relative_to(ROOT).as_posix(),sha256=sha(f),board=True,hardware=True,web_live_verified=True,owner_still_live=True,promoted=False),'## M544演示20分钟退出与错误等待提示修复已实际验证07\n\nRESULT SHA '+sha(f)+'；新会话'+session+'实际固定预热后一次视频7任务'+e['id']+'返回Yes，实际首判断'+str(v['TTFT_s'])+'秒，原用户页红警截图保存，0为检查器重跑模型。断开/初始化/传图明确分开；配置21600秒窗口、主机22800秒、最多12新任务，CPU及A53生命周期边界通过，但未做6小时持续实测。数学/码/scale/权重保持，Import06路径拒绝保留仅07隔离。当前七owner有意常驻，不称退出或稳定恢复；仅7.512秒采样图。旧成功05会话元数据已原字节双份+板gzip无损归档，其他旧历史/失败/权重/稳定未改。')
print(r['status'],e['id'],r['TTFT_s'])
