"""Launch one versioned bounded live bridge after real A53/Web prerequisite admission."""
import argparse,hashlib,json,subprocess,sys,uuid,msvcrt,urllib.request
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2];HERE=Path(__file__).resolve().parent;RUNS=ROOT/'deployment/mage_vl4b/optimization_v1/runs'
sys.path.insert(0,str(ROOT/'scripts/optimization'))
from m455456_workflow02 import synchronized
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
read=lambda p:json.loads(Path(p).read_bytes())
def save(p,v):p.parent.mkdir(parents=True,exist_ok=True);p.open('x',encoding='utf-8').write(json.dumps(v,ensure_ascii=False,indent=2)+'\n')
def launch():
    ap=argparse.ArgumentParser();ap.add_argument('--api',default='http://127.0.0.1:8766');ap.add_argument('--purpose',choices=['web-validation','operator-demo'],default='operator-demo');a=ap.parse_args()
    assert a.api=='http://127.0.0.1:8766','Only the fixed local demonstration server is admitted'
    with urllib.request.urlopen(a.api+'/api/state',timeout=5) as response:state=json.load(response)
    assert state.get('web_source_sha256')==sha(HERE/'live_server.py'),'Restart the owned local server before a board launch'
    assert state.get('worker') is None,'An existing worker owns the connection; no duplicate launch'
    binding=read(HERE/'LIVE_BINDING.json');assert state.get('worker_package_sha256')==binding['package_manifest_sha256'],'Server binding is stale; restart only the owned local server'
    prep=read(ROOT/binding['worker_preparation']);imported=ROOT/binding['worker_import_result']
    if not imported.is_file():raise SystemExit('Actual board A53 Import has not passed; no model command sent. Preview remains available.')
    v=read(imported);assert v['primary_rc']==0 and v['package_manifest_sha256']==prep['manifest_sha256'] and v['CPU_components']['live_frame_protocol']['negative_cases']==13
    for n in ['CURRENT_STATE.md','docsMILESTONES.md','deployment/mage_vl4b/BOARD_GATE_RESULT.json']:assert sha(imported) in (ROOT/n).read_text(encoding='utf-8-sig')
    binding=read(HERE/'LIVE_BINDING.json');assert binding['package_manifest_sha256']==prep['manifest_sha256']
    session=uuid.uuid4().hex;out=RUNS/'M544-live-worker-instances'/session;out.mkdir(parents=True,exist_ok=False);logs=ROOT/'tmp/m544_live_instances'/session;logs.mkdir(parents=True,exist_ok=False)
    bridge=HERE/'live_uart.ps1';command='sudo -n bash '+prep['remote']+'/run.sh '+prep['runner_sha256']+' '+prep['manifest_sha256']+' '+session
    active=dict(status='STARTED_M544_ONE_BOUNDED_LIVE_WORKER_RESULT_PENDING',session=session,purpose=a.purpose,command=command,bridge_sha256=sha(bridge),package_manifest_sha256=prep['manifest_sha256'],max_new_prefills=13,web_jobs_maximum=12,readiness_requires_real_warmup=True,raw_log=(logs/'UART.log').relative_to(ROOT).as_posix(),no_signals_or_retries=True)
    save(out/'STARTED.json',active);h=sha(out/'STARTED.json');synchronized('latest_m544_worker_active',dict(status=active['status'],result=(out/'STARTED.json').relative_to(ROOT).as_posix(),sha256=h,board=True,owner_still_live=True,promoted=False),'## M544唯一新网页工作器启动\n\nRESULT SHA '+h+'；会话'+session+'，用途'+a.purpose+'，原1预热+最多12实际新任务，逐nonce/输入SHA/原完整词表。只跟踪此原会话，不再启动或发送信号；尚未称完成/网页验收。')
    pwsh='C:/Users/30429/.cache/codex-runtimes/codex-primary-runtime/dependencies/native/powershell/pwsh.exe';raw=logs/'host.raw'
    with raw.open('xb') as f:rc=subprocess.run([pwsh,'-NoProfile','-File',str(bridge),'-Command',command,'-LogPath',(logs/'UART.log').relative_to(ROOT).as_posix(),'-Session',session,'-Manifest',prep['manifest_sha256'],'-Api',a.api],cwd=ROOT,stdout=f,stderr=subprocess.STDOUT).returncode
    save(out/'HOST_EXIT.json',dict(original_host_rc=rc,raw_sha256=sha(raw),UART_sha256=sha(logs/'UART.log') if (logs/'UART.log').exists() else None))
    sys.path.insert(0,str(ROOT/'experiments/pruning_plan_20261020'));from M455_P1_shape_prepare52303 import decode_shape
    try:v,b=decode_shape((logs/'UART.log').read_text(encoding='utf-8-sig'))
    except BaseException:
        pending=dict(status='STOP_M544_HOST_RESULT_NEEDS_ORIGINAL_LOG_INSPECTION_NO_REPLAY',primary_rc=rc,session=session,raw_sha256=sha(raw),board_result_not_collected=True,signals=0,retries=0);save(out/'RESULT.json',pending);h=sha(out/'RESULT.json')
        synchronized('latest_m544_worker_active',dict(status=pending['status'],result=(out/'RESULT.json').relative_to(ROOT).as_posix(),sha256=h,board=True,promoted=False),'## M544网页工作器原结果待查\n\nRESULT SHA '+h+'；原host'+str(rc)+'，只查原日志/保存字节，不重跑、信号、free或reset。');raise
    (out/'BOARD_RESULT.json').open('xb').write(b);assert v['primary_rc']==rc
    if rc==0:assert v['safe_cleanup_complete'] and not v['unsafe_retained'] and v['clock_initial']==v['clock_final'] and len(v['releases'])==7 and v['releases']==list(reversed(v['allocations']))
    result=dict(status='COMPLETE_M544_BOUNDED_WEB_WORKER_ORIGINAL_RESULT',primary_rc=rc,session=session,board_sha256=sha(out/'BOARD_RESULT.json'),prefills=v.get('model_forwards'),live_jobs=v.get('live_jobs_returned'),safe_cleanup=v.get('safe_cleanup_complete'),unsafe_retained=v.get('unsafe_retained'),purpose=a.purpose);save(out/'RESULT.json',result);h=sha(out/'RESULT.json')
    synchronized('latest_m544_worker_active',dict(status=result['status'],result=(out/'RESULT.json').relative_to(ROOT).as_posix(),sha256=h,board=True,hardware=True,promoted=False),'## M544网页工作器原作用域完成\n\nRESULT SHA '+h+'；原host/native'+str(rc)+'，会话'+session+'。实际warm/live次数和七owner/稳定四clock按原BOARD_RESULT；不把单次请求已返回当作整体退出。原记录保留，不重跑补报告。')
    print(json.dumps(result,ensure_ascii=False),flush=True);return rc
def main():
    lock=HERE/'var/live/worker_launch.lock';lock.parent.mkdir(parents=True,exist_ok=True)
    with lock.open('a+b') as f:
        if f.tell()==0:f.write(b'0');f.flush()
        f.seek(0)
        try:msvcrt.locking(f.fileno(),msvcrt.LK_NBLCK,1)
        except OSError:raise SystemExit('A live bridge is already running; no duplicate launch or board command sent.')
        try:return launch()
        finally:f.seek(0);msvcrt.locking(f.fileno(),msvcrt.LK_UNLCK,1)
if __name__=='__main__':raise SystemExit(main())
