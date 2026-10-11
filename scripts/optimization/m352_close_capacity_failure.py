"""Adjudicate saved M352 bytes only; never access COM3 or rerun the gate."""
import hashlib
import json
from pathlib import Path
import re
import sys
sys.dont_write_bytecode = True
import m352_workflow as gate
import m351_workflow as w

ROOT = Path(__file__).resolve().parents[2]
BASE = ROOT / 'deployment/mage_vl4b/optimization_v1'
RUN = BASE / 'runs/M352-load-ps-slot-board-01'
RAW_SHA = '325511dd0c5a2f1a57a039c46edbbb9ba867db0012089db824880cba616fd687'


def main():
    output = RUN / 'INTERPRETATION.json'
    if output.exists(): raise RuntimeError('Closure already exists; inspect only')
    texts = {n: (ROOT/n).read_text(encoding='utf-8-sig') for n in
             ('CURRENT_STATE.md','DEPLOYMENT_OPERATION_MISTAKES_REVIEW.md','docsMILESTONES.md','deployment/mage_vl4b/BOARD_GATE_RESULT.json')}
    assert all(RAW_SHA in texts[n] for n in ('CURRENT_STATE.md','docsMILESTONES.md'))
    board = json.loads(texts['deployment/mage_vl4b/BOARD_GATE_RESULT.json'])
    assert board['latest_m352_load_ps_slot_board']['sha256'] == RAW_SHA
    raw = (RUN/'BOARD_RESULT.json').read_bytes()
    assert hashlib.sha256(raw).hexdigest() == RAW_SHA
    logpath = ROOT/'tmp/m352/load_slot_uart.log'
    log = logpath.read_text(encoding='utf-8-sig')
    digest, recovered, result = gate.decode(log)
    assert digest == RAW_SHA and recovered == raw
    assert 'M352_DONE gate_rc=1 export_rc=0' in log
    assert result['status'] == 'FAIL_LOAD_ONLY_PS_SLOT_CAPACITY'
    assert result['gate_return_code'] == 1 and result['host_calls'] == result['logical_calls'] == result['fpga_transactions'] == 0
    assert not result['worker_started'] and result['model_forward_calls'] == 0
    assert result['ps_slot'] == {} and result['ps_slot_port_count_before_release'] == 0
    allocated, released = result['allocated_buffers'], result['released_buffers']
    assert len(allocated) == len(released) == 7
    assert released == list(reversed(allocated))
    assert len({r['address'] for r in allocated}) == 7
    assert result['safe_buffers_released'] and not result['unsafe_buffers_retained']
    assert result['original_buffer_release_count'] == 7
    assert result['loaded_snapshot'] == result['final_snapshot']
    from ps_slot_capacity import never_submitted_release
    assert never_submitted_release(result['final_snapshot'], 0, 0, result['blocked_inference_attempts'], 7)
    assert log.count('RuntimeError: Duplicate original-buffer free refused') == 7
    assert log.count('Exception ignored in: <function PynqBuffer.__del__') == 7
    assert log.index('M352_RESULT_SAVED') < log.index('Exception ignored in:') < log.index('M352_RESULT_SHA256=')
    eligibility = result['pre_slot_eligibility']
    gap = eligibility['required_cma_bytes'] - eligibility['cma_free_bytes']
    assert gap == 29192192 and eligibility['mem_available_bytes'] >= eligibility['required_mem_available_bytes']
    closure = dict(status='CLOSED_PRE_SLOT_CMA_REJECTION_NO_CANDIDATE_RUN',build_id='0x4D395832',
        raw_sha256=digest,uart_log=str(logpath.relative_to(ROOT)).replace('\\','/'),uart_log_sha256=w.sha(logpath),
        strict_recovery_chunks=8,gate_return_code=1,export_return_code=0,
        retained_runtime_cma_bytes=eligibility['cma_free_bytes'],cma_required_bytes=eligibility['required_cma_bytes'],
        cma_missing_bytes=gap,retained_runtime_mem_available_bytes=eligibility['mem_available_bytes'],
        ps_slot_allocated=False,worker_started=False,model_forward_calls=0,fpga_transactions=0,
        all_seven_backend_releases_recorded_once=True,never_submitted_lifecycle=True,completed_dma_idle_proven=False,
        destructor_warning_count=7,destructor_warning_cause='Diagnostic hook rejects a repeated freebuffer call after recorded successful backend release; callback raises before a second backend call',
        destructor_issue_in_raw_json=False,post_result_uart_exception_preserved=True,
        original_frozen_package_unchanged=True,board_gate_rerun=False,
        candidate_memory_capacity_proven=False,numerical_pass=False,performance_pass=False,promoted=False,
        conclusions=['Ordinary available memory passed; this is a conservative CMA threshold rejection before slot allocation',
                     'Not proof of total 4GB exhaustion, failed bank allocation, page ownership, fragmentation, or prefetch lack of benefit',
                     'Post-close CMA is not retained-runtime capacity evidence'],
        next_step='Offline original allocation/lifetime feasibility audit and future idempotent release-hook regression; no runtime, video, numeric or performance retry')
    w.atomic(output,w.encoded(closure),immutable=True)
    sha = w.sha(output)
    note = ('## M352 容量失败独立闭合与析构钩子问题（2026-10-01）\n\n'
        '稳定Build0x4D395832；原始SHA `'+RAW_SHA+'`，原rc1/export0、8块完整回收，7块原DMA按地址/字节逆序各释放一次。'
        '完整runtime保留时CmaFree36.160156MiB，距64MiB余量缺27.839844MiB；MemAvailable约2911.289062MiB已满足普通内存门槛。'
        '拒绝发生在PS slot分配前，0slot/worker/forward/FPGA事务，不能评价预读收益或称4GB耗尽。'
        'AP4/return0/两DMASR0仅从未提交生命周期。结果保存后7条PynqBuffer析构警告来自诊断钩子误拒绝幂等freebuffer；'
        '第二次调用在后端free前被拒绝，原日志/原包/原结果保留，不重跑诊断。'
        f'闭合 `{output.relative_to(ROOT).as_posix()}` SHA `{sha}`。'
        '下一步仅离线审计原分配和生命周期、修复后续诊断释放钩子；容量/新候选硬件数值/视频性能未解锁，稳定源/服务/回滚/boot/DTB/CMA保持。\n\n')
    w.sync('latest_m352_capacity_failure_closure',dict(status=closure['status'],result=output.relative_to(ROOT).as_posix(),sha256=sha,
        raw_sha256=RAW_SHA,cma_missing_bytes=gap,destructor_warning_count=7,memory_capacity_proven=False,performance_pass=False,next_step=closure['next_step']),note)
    w.atomic(RUN/'REPORT.md',('# M352 完整runtime容量失败闭合\n\n'+note).encode('utf-8'))
    review = ROOT/'DEPLOYMENT_OPERATION_MISTAKES_REVIEW.md'
    title, rest = review.read_text(encoding='utf-8-sig').split('\n',1)
    w.atomic(review,(title+'\n\n'+note+rest.lstrip('\n')).encode('utf-8'))
    print(json.dumps(dict(status=closure['status'],sha256=sha,gap_mib=gap/(1<<20),backend_frees=7)))


if __name__ == '__main__': main()
