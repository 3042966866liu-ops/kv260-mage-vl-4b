"""Close stale revision03 status without inventing a simulator return code."""
import json
import time
from m351_workflow import ROOT,BASE,HERE,atomic,encoded,sha,sync
from m441_supervisor04 import process,boot,log_snapshot,selftest

def main():
    out=BASE/'runs/M441-revision03-interruption-closure-01'
    ev=out/'RESULT.json'
    if ev.exists():raise RuntimeError('Existing closure: read only')
    old=BASE/'runs/M441-revision03-continuation-01'
    start=json.loads((old/'START.json').read_bytes());running=json.loads((old/'RUNNING.json').read_bytes())
    current=boot()
    owner=process(start['pid'],running['creation_FILETIME'])
    child=process(running['phase']['pid'])
    review=BASE/'runs/M441-day-review-01/RESULT.json'
    r=json.loads(review.read_bytes())
    assert r['status']=='INCOMPLETE_M441_REVISION03_HOST_REBOOT_READ_ONLY_REVIEW'
    assert current['boot_epoch_estimate']>start['epoch']+60
    assert owner['status'] in ('NOT_FOUND','PID_REUSED','EXITED') and child['status']!='ALIVE'
    p=old/'PROGRESS.json';before=p.read_bytes();rows=json.loads(before)
    assert rows[-1]['status']=='RUNNING'
    atomic(old/'PROGRESS_BEFORE_HOST_REBOOT_CLOSURE.json',before,immutable=True)
    snap=log_snapshot(ROOT/'tmp/m441_long_A_gate_up_03/verilog/random.log')
    assert snap['last']['cycle']==38500000 and snap['last']['output']==273408
    checks=selftest()
    result=dict(status='INTERRUPTED_HOST_REBOOT_NO_SIMULATION_VERDICT',board=False,build_id='0x4D343431',
        original_review_sha256=sha(review),historical_RUNNING_sha256=sha(old/'RUNNING.json'),
        original_progress_sha256=sha(old/'PROGRESS_BEFORE_HOST_REBOOT_CLOSURE.json'),
        last_progress=snap,host=current,supervisor=owner,child=child,checks=checks,
        original_simulation_return_code=None,formal_simulation_pass=False,
        simulation_restart=False,processes_killed=False,checkpoint_resume_available=False,
        source_sha256=sha(HERE/'m441_reconcile04.py'),observer_sha256=sha(HERE/'m441_supervisor04.py'))
    atomic(ev,encoded(result),immutable=True)
    rows.append(dict(epoch=time.time(),stage='host_reconciliation',status=result['status'],
        last_cycle=38500000,last_output_words=273408,expected_output_words=311296,
        closure_result=ev.relative_to(ROOT).as_posix(),sha256=sha(ev),simulation_return_code=None))
    atomic(p,encoded(rows))
    atomic(old/'STATUS.json',encoded(dict(status=result['status'],sha256=sha(ev),
        result=ev.relative_to(ROOT).as_posix(),last_cycle=38500000,last_output_words=273408,
        historical_running_snapshot_retained=True)),immutable=True)
    board=json.loads((ROOT/'deployment/mage_vl4b/BOARD_GATE_RESULT.json').read_bytes())
    historical=board['latest_m441_revision03_running']
    sync('historical_m441_revision03_running',historical,
         '## M441 revision03 历史启动快照保留\n\nSHA '+historical['sha256']+'；此项仅表示当时启动，不表示当前进程仍运行。')
    value=dict(status=result['status'],result=ev.relative_to(ROOT).as_posix(),sha256=sha(ev),board=False)
    sync('latest_m441_revision03_running',value,
         '## M441 revision03 残留运行状态已对账（2026-10-08）\n\nSHA '+sha(ev)+'；主机重启中断。保留原RUNNING与原PROGRESS精确字节，PROGRESS追加中断终态，最后38.5M周期/273408字；无模拟器正常rc/完整PASS，不可续跑。PID＋FILETIME/启动时间检查及9项有界状态检查通过；0重启仿真/kill/板端。下一步独立冻结数值、针对性压力与实板性能协议。')
    print(result['status'],sha(ev))

if __name__=='__main__':main()
