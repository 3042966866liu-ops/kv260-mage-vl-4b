"""Close the exited controller from its already collected immutable raw result."""
import json
import m351_workflow as w
from m441_host_io08 import atomic

def main():
    b=json.loads((w.ROOT/'deployment/mage_vl4b/BOARD_GATE_RESULT.json').read_bytes())
    raw=b['latest_m441_complete_request_board']; closure=b['latest_m441_complete_request_closure']
    for row in (raw,closure):
        assert w.sha(w.ROOT/row['result'])==row['sha256']
        assert all(row['sha256'] in (w.ROOT/n).read_text(encoding='utf-8') for n in ('CURRENT_STATE.md','docsMILESTONES.md'))
    r=json.loads((w.ROOT/raw['result']).read_bytes())
    assert r['gate_return_code']==1 and not r.get('samples') and r['safe_buffers_released'] and not r['unsafe_buffers_retained'] and r['stable_overlay_reloaded']
    out=w.BASE/'runs/M441-performance-execution-11/RESULT.json'
    value=dict(status='STOPPED_M441_FIRST_SWITCH_CMA_GUARD11',original_gate_rc=1,controller_exited=True,raw_sha256=raw['sha256'],closure_sha256=closure['sha256'],
               complete_requests=0,formal_samples=0,fpga_transactions=r['fpga_transactions'],original_seven_released=r['original_buffer_release_count'],stable_overlay_restored=True,
               old_attempt_closed=True,full_request_performance_proven=False,next_step='One separate bounded first-switch allocation trace, retaining the original CMA guard and zero model requests')
    atomic(out,w.encoded(value),immutable=True); digest=w.sha(out)
    w.sync('latest_m441_performance_execution',dict(status=value['status'],result=out.relative_to(w.ROOT).as_posix(),sha256=digest),
           f'## M441 性能控制11末态对账（2026-10-09）\n\nSHA {digest}；原控制已退出rc1，原raw {raw["sha256"]}和裁决{closure["sha256"]}完整保留。首次B→A最小事务通过但CMA累计计数变化触发旧检查，0请求/0正式样本；七缓冲释放、稳定核恢复。不存在仍运行性能程序；只调试切核资源级，旧09不重跑或加样本。')
    notified=w.BASE/'runs/M441-completion-notification-08/NOTIFIED.json'
    n=json.loads(notified.read_bytes())
    n.setdefault('stages',{})['performance_guard_failed11']=dict(raw_sha256=raw['sha256'],closure_sha256=closure['sha256'],terminal_sha256=digest,notified_in_current_chat=True)
    atomic(notified,w.encoded(n))
    print(value['status'],digest)

if __name__=='__main__':main()
