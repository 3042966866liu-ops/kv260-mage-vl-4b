"""Freeze software-only alarm-position correction; do not contact board."""
from pathlib import Path
import hashlib,json,sys,urllib.request
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[1]
out=ROOT/'deployment/mage_vl4b/optimization_v1/runs/M544-alarm-no-seek-UI-09'
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
old="v.pause();v.loop=false;v.currentTime=upload.cases[0].timestamp_ms/1000"
assert old in (out/'before_playback_live.js').read_text(encoding='utf-8')
assert old not in (HERE/'static/playback_live.js').read_text(encoding='utf-8')
qa=HERE/'qa/alarm_no_seek09/RESULT.json';q=json.loads(qa.read_bytes())
assert q['FPGA_runs']==0 and q['fake_predictions'] and len(q['checks'])==13
with urllib.request.urlopen('http://127.0.0.1:8766/static/playback_live.js?v=alarm-no-seek09',timeout=5) as r:
    served=r.read()
assert served==(HERE/'static/playback_live.js').read_bytes()
result=dict(status='PASS_SOFTWARE_UI_ALARM_PRESERVES_PLAYBACK_POSITION',primary_rc=0,
    root_cause='Actual Yes handler paused video and explicitly assigned currentTime to the sampled input timestamp. Video07 sampled at 7512ms, so completion forced a rewind to7.512s.',
    fix='Pause at current playback position, no alarm-triggered seek; sampled evidence and timestamp remain separately visible.',
    scope='One selected image per playback, not continuous whole-video detection; decision refers to sampled image.',
    old_source_sha256=sha(out/'before_playback_live.js'),
    sources={str(p.relative_to(ROOT)):sha(p) for p in [HERE/'static/playback_live.js',HERE/'static/demo.html',HERE/'qa_alarm_no_seek09.cjs',HERE/'run_alarm_no_seek09.py']},
    QA_result=str(qa.relative_to(ROOT)),QA_sha256=sha(qa),QA_original_process_rc=0,
    QA_method='Isolated8767 separate database, synthetic Yes/No only. Playback5.5s differs from sampled input; after Yes currentTime unchanged within0.05s. Remaining12 presentation checks preserved.',
    live_static_response_matches=True,live_worker_not_restarted=True,board_commands=0,new_model_runs=0,
    performance_or_quality_claim=False,
    preparation_metadata_correction='PREPARATION.json root_cause accidentally stored the final replacement-match variable rather than the alarm expression. Before source bytes preserved; this RESULT states and asserts the actual root cause. No model affected.')
f=out/'RESULT.json';f.open('x',encoding='utf-8').write(json.dumps(result,ensure_ascii=False,indent=2)+'\n');h=sha(f)
note='报警跳回7秒是网页Yes回调主动设置currentTime为实际采样点7.512秒，属于交互设计错误，非模型/硬件导致。已删自动seek，只暂停在结果返回时播放位置，采样缩略图及时间单列；单次判断仍只对应采样图，不冒充全视频连续监控。独立8767数据库13项软件回归通过，含播放5.5秒且采样时间不同的报警不跳转检查；合成结果明确不当实板证据。8766实际静态文件SHA匹配，0新模型/板命令/工作器重启，无速度或质量提升声明。刷新页面加载新版本。旧JS/HTML及准备元数据原字节保留，准备字段变量误引用在最终RESULT纠正。'
(out/'REPORT.md').open('x',encoding='utf-8').write('# 报警自动跳回采样点的修正\n\n'+note+'\n\nRESULT SHA '+h+'\n')
sys.path.insert(0,str(ROOT/'scripts/optimization'));from m455456_workflow02 import synchronized
synchronized('latest_m544_alarm_no_seek_UI09',dict(status=result['status'],result=f.relative_to(ROOT).as_posix(),sha256=h,board=False,hardware=False,promoted=False),'## M544报警保持当前播放位置修正09\n\nRESULT SHA '+h+'；'+note)
print(result['status'],h)
if __name__=='__main__':pass
