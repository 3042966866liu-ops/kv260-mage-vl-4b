"""Audit this original boot05 video07 request and actual visible alarm; no model calls."""
from pathlib import Path
import hashlib,json,sys,urllib.request
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[1];RUNS=ROOT/'deployment/mage_vl4b/optimization_v1/runs'
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
read=lambda p:json.loads(Path(p).read_bytes())
SESSION='5b07f571df6342f4a39f58e919b5eec1';UPLOAD='3c26abf6c51141af809d824cb7c868e7'
out=RUNS/'M544-current-boot-operator-demo-05';assert (out/'actual_alarm.png').is_file()
with urllib.request.urlopen('http://127.0.0.1:8766/api/state',timeout=4) as r:state=json.load(r)
w=state['worker'];assert w and w['session']==SESSION and w['warm']
events=[e for e in state['events'] if e['kind']=='live' and e.get('upload_id')==UPLOAD and e.get('decision')=='Yes' and (RUNS/'M544-live-board-results'/SESSION/e['id']/'RESULT.json').is_file()]
assert len(events)==1,'Audit only the one original completed video07 request, never rerun for the checker'
e=events[0];proof=RUNS/'M544-live-board-results'/SESSION/e['id']/'RESULT.json';v=read(proof)
binding=read(HERE/'LIVE_BINDING.json');prep=read(ROOT/binding['worker_preparation']);plan=read(ROOT/prep['package']/'DEMO_BOARD_PLAN.json')
assert v['session']==SESSION and v['decision']=='Yes' and v['primary_rc']==0 and v['completed_request'] and v['argmax_verified'] and v['actual_full_vocab']==151936
assert v['package_manifest_sha256']==binding['package_manifest_sha256'] and plan['expected_boot']==binding['worker_expected_boot']=='f425c270-dc5e-4a1d-98de-025c85938620'
assert v['case_id']=='u'+UPLOAD+'_f0' and v['frame_sha256']=='1d8c3b1fe46320f44891618b83e9dab03d2c2d29a607d3cfd14d53820d44e6b1'
assert v['physical_calls']>=324 and v['owner_released'] is False and v['stable_restored'] is False
fixed=RUNS/'M544-live-fixed-gates'/SESSION/'RESULT.json';a=read(fixed);assert a['primary_rc']==0 and a['answer_correct'] and a['boot_id']==plan['expected_boot']
screen=read(out/'BROWSER_OBSERVATION.json');assert screen['alarm_visible'] and screen['video_paused'] and screen['no_latency_text'] and screen['sample_timestamp_ms']==7512
result=dict(status='PASS_CURRENT_BOOT_VIDEO07_REAL_FPGA_AND_VISIBLE_WEB_ALARM',primary_rc=0,session=SESSION,job=e['id'],boot_id=plan['expected_boot'],decision=v['decision'],TTFT_s=v['TTFT_s'],proof_sha256=sha(proof),proof_path=proof.relative_to(ROOT).as_posix(),fixed_gate_sha256=sha(fixed),screenshot_sha256=sha(out/'actual_alarm.png'),browser_observation_sha256=sha(out/'BROWSER_OBSERVATION.json'),package_manifest_sha256=binding['package_manifest_sha256'],input_frame_sha256=v['frame_sha256'],full_logits_sha256=v['full_logits_sha256'],actual_full_vocab=151936,model_runs_in_audit=0,original_fixed_warmup=1,original_video07_requests=1,worker_still_live=True,owners_still_live=True,stable_restoration_claim=False,sample_only_not_whole_video=True,No_UI_software_regression_sha256=sha(HERE/'qa/input_selection05/RESULT.json'),only_authorized_WARM_A_copy_removed=True,no_new_optimization=True)
f=out/'RESULT.json';f.open('x',encoding='utf-8').write(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
(out/'REPORT.md').open('x',encoding='utf-8').write('# 当前启动演示恢复\n\n新boot独立依赖逐级恢复及Import闭合后，唯一工作器完成一次固定预热和一次视频7真实请求。该请求返回Yes并在用户原网页显示红色报警；原151936词表argmax/nonce/帧/包SHA绑定，未使用历史答案或定时器报警。截图为实际用户页。本次识别对应7.512秒采样图，不当全片连续监控或泛化证明。工作器及七owner有意常驻供后续演示，未称退出或稳定恢复。No静默、不显示TTFT、不回跳采样时点的软件回归保持。\n\n原文件回收仅本次授权WARM_A一份；其他历史模型和失败不动。本轮私有失效缓存已电脑双份原字节及RAM gzip保全。网络恢复已核。\n\nRESULT SHA '+sha(f)+'\n')
sys.path.insert(0,str(ROOT/'scripts/optimization'));from m455456_workflow02 import synchronized
synchronized('latest_m544_operator_demo05',dict(status=result['status'],result=f.relative_to(ROOT).as_posix(),sha256=sha(f),board=True,hardware=True,web_live_verified=True,owner_still_live=True,promoted=False),'## M544当前启动视频7实际网页报警已闭合05\n\nRESULT SHA '+sha(f)+'；boot '+plan['expected_boot']+'、会话'+SESSION+'，原一次固定预热通过后一次新视频7请求'+e['id']+'返回Yes，实际首判断'+str(v['TTFT_s'])+'秒；151936词表argmax/实际输入/包及新nonce全SHA核，原用户页醒目红警截图保存，不复用旧结果。仅7.512秒采样图；无刀静默/无TTFT文案/不自动跳回软件回归保持。工作器仍有意常驻、七owner未释放、不称稳定恢复或泛化通过。仅本次授权一份M533 WARM_A旧成功数组回收，所有其他历史/失败/权重/稳定保持。已暂停新优化，演示就绪。')
print(result['status'],e['id'],v['TTFT_s'])
