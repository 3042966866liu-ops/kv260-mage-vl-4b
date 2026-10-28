"""Observe the one running operator session; do not stop it or claim its owners released."""
import hashlib,json,sys,urllib.request
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2];RUNS=ROOT/'deployment/mage_vl4b/optimization_v1/runs'
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
def main():
    with urllib.request.urlopen('http://127.0.0.1:8766/api/state',timeout=5) as r:s=json.load(r)
    w=s['worker'];assert w and w['session']=='4fb30b05f2f94921a8e0bf9c88f02fc9' and w['warm'] and w['ready']
    fixed=RUNS/'M544-live-fixed-gates'/w['session']/'RESULT.json';assert json.loads(fixed.read_bytes())['answer_correct']
    passed=RUNS/'M544-live-Web-final-audit-03/RESULT.json';assert json.loads(passed.read_bytes())['primary_rc']==0
    out=RUNS/'M544-operator-ready-03';out.mkdir(exist_ok=False)
    v=dict(status='RUNNING_M544_OPERATOR_DEMO_WARM_READY',session=w['session'],package_manifest_sha256=w['package_manifest_sha256'],actual_API_worker=w,current_fixed_gate_sha256=sha(fixed),closed_Web_validation_audit_sha256=sha(passed),actual_web_live_verified=True,kept_running_for_user=True,current_scope_not_closed=True,current_scope_not_claimed_released=True,original_exec_session=92124,ordinary_stop_only=True,no_new_model_calls_in_this_record=0,preview='http://127.0.0.1:8766/')
    p=out/'RESULT.json';p.write_text(json.dumps(v,ensure_ascii=False,indent=2)+'\n',encoding='utf-8');h=sha(p)
    sys.path.insert(0,str(ROOT/'scripts/optimization'));from m455456_workflow02 import synchronized
    synchronized('latest_m544_operator_ready03',dict(status=v['status'],result=p.relative_to(ROOT).as_posix(),sha256=h,board=True,hardware=True,web_live_verified=True,operator_session_live=True,promoted=False),'## M544供人类操作的唯一演示工作器已预热就绪\n\nRESULT SHA '+h+'；实际API会话'+w['session']+' ready/warm均True、当前启动固定预热已同步。原测试会话c9b7已2网页样例/7owner/stable四clock闭合并审计；新操作会话故意保留供网页，不称本新作用域已释放或退出。仅原exec92124，后续不重建/重复Run，最多12新任务/空闲1200秒普通收尾，需停用normal data-stop。页面无TTFT，实际Yes大红警示、No静默；首次素材传输在播放前准备，每播放一代表帧，非连续全视频扫描。')
    print(v['status'],h)
if __name__=='__main__':main()
