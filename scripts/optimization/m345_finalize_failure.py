"""Close M345 memory rejection and control repair; never rerun hardware."""
import hashlib
import json
import os
from pathlib import Path
import re
ROOT=Path(__file__).resolve().parents[2]
RUN=ROOT/'deployment/mage_vl4b/optimization_v1/runs/M345-fixed-video-board-01'
SHA='b149cf6d4e031628c4ff43c99f6e4579575a64598ee55d80e35c2f7ff48e8fd4'


def atomic(path,data):
    part=path.with_name(path.name+'.failure-part')
    with part.open('wb') as f: f.write(data); f.flush(); os.fsync(f.fileno())
    os.replace(part,path)


def main():
    path=RUN/'BOARD_RESULT.json'; raw=path.read_bytes(); result=json.loads(raw)
    assert hashlib.sha256(raw).hexdigest()==SHA and result['status']=='FAIL'
    assert result['safe_buffers_released'] and not result['unsafe_buffers_retained'] and len(result['passes'])==1 and result.get('prefetch') is None
    log=(ROOT/'tmp/m345/post_failure_meminfo_uart.log').read_text(encoding='utf-8-sig')
    assert '__M345_MEMINFO_RC_0__' in log
    memory={key:int(value)*1024 for key,value in re.findall(r'(?m)^(MemTotal|MemAvailable|Cached|AnonPages|CmaTotal|CmaFree):\s+(\d+) kB',log)}
    required=27852800+(64<<20)
    repair=ROOT/'deployment/mage_vl4b/optimization_v1/runs/M345-failure-closure-01'; repair.mkdir(parents=True,exist_ok=True)
    closed=dict(status='FAIL_CMA_REJECTION_SAFELY_CLOSED',board_result_sha256=SHA,candidate_prefill_launched=False,
        cma_after_runtime=result['cma_after_actual_runtime_allocations'],cma_before_candidate=result['cma_before_extra_bank_after_baseline_and_candidate_vision'],
        extra_bank_bytes=27852800,reserve_bytes=64<<20,required_free_bytes=required,post_exit_memory_bytes=memory,
        post_exit_snapshot_scope='After process exit and safe release; not serving-time capacity evidence',
        collector_repair='Terminating UART exception bypassed automatic collector; collected same 209 exact chunks manually rc0, no hardware rerun; try/catch now always collects',
        controller_self_test='PASS terminating-gate-failure-collects and collector-failure-stops; no COM3/FPGA',
        controller_sha256=hashlib.sha256((ROOT/'scripts/optimization/m345_run_and_collect.ps1').read_bytes()).hexdigest(),
        hardware_rerun=False,performance_pass=False,next_step='Bounded load-only memory/CMA diagnosis with PS-only GC/glibc trim observations, no model forward; require unchanged 90.5625MiB free threshold before any numerical retry')
    atomic(repair/'RESULT.json',(json.dumps(closed,indent=2)+'\n').encode('utf-8'))
    repair_sha=hashlib.sha256((repair/'RESULT.json').read_bytes()).hexdigest()
    note=('## M345 CMA门槛失败闭合（2026-10-01）\n\n'
        '稳定Build `0x4D395832`；M345完整原159视频基线完成，Token15/文本0/ABSENT/score0.4416730056646256、778逻辑/781物理事务、3语言保护重试、2,034,890,752B暂存。'
        '真实完整runtime加载后CmaFree仅19,832,832B（18.914MiB），候选视觉结束后的Prefill入口为53,346,304B（50.875MiB），低于第二bank27,852,800B加64MiB预留合计94,961,664B（90.5625MiB）。'
        '候选预取worker/额外bank/语言FPGA计算均未启动；没有候选logits/KV完整比对或性能通过。末态AP_CTRL4/两DMA4098、无错误，缓冲安全释放，未kill/reset。'
        '原始FAIL `deployment/mage_vl4b/optimization_v1/runs/M345-fixed-video-board-01/BOARD_RESULT.json` SHA `'+SHA+'`，209分块精确回收且三份记录同步。'
        '进程退出后只读CmaFree232,644,608B（221.867MiB）/CmaTotal838,860,800B；该空闲快照不是运行时容量证明。'
        'UART非零异常最初跳过自动收集，已只回收原字节、没有重跑硬件；控制器加try/catch确保失败也收集，并通过故意失败自测。'
        '闭合证据 `deployment/mage_vl4b/optimization_v1/runs/M345-failure-closure-01/RESULT.json` SHA `'+repair_sha+'`。'
        '下次必须在昂贵基线前检查完整runtime加载后的90.5625MiB门槛；先做有界只加载内存诊断和PS空闲堆回收观测，不进行模型forward，不改boot/DTB/CMA、不降低64MiB余量、不drop_caches。'
        '稳定源/服务/回滚不变；无提速或晋级。M346性能计划暂未解锁，先留在fixed159视频/CMA失败级。\n\n')
    names=('CURRENT_STATE.md','docsMILESTONES.md','DEPLOYMENT_OPERATION_MISTAKES_REVIEW.md','deployment/mage_vl4b/BOARD_GATE_RESULT.json')
    for name in names:
        backup=repair/(Path(name).name+'.before')
        if not backup.exists(): backup.write_bytes((ROOT/name).read_bytes())
    board_path=ROOT/names[-1]; board=json.loads(board_path.read_text(encoding='utf-8'))
    assert board['latest_m345_fixed_video']['sha256']==SHA
    board['latest_m345_fixed_video'].update(candidate_prefill_launched=False,cma_before_candidate=closed['cma_before_candidate'],
        required_free_bytes=required,failure_closure_result='deployment/mage_vl4b/optimization_v1/runs/M345-failure-closure-01/RESULT.json',failure_closure_sha256=repair_sha,next_step=closed['next_step'])
    atomic(board_path,(json.dumps(board,ensure_ascii=False,indent=2)+'\n').encode('utf-8'))
    for name in names[:3]:
        target=ROOT/name; content=target.read_text(encoding='utf-8')
        if repair_sha not in content:
            heading,rest=content.split('\n',1); atomic(target,(heading+'\n\n'+note+rest.lstrip('\n')).encode('utf-8'))
    atomic(RUN/'REPORT.md',('# M345 固定159视频数值门禁：CMA条件未通过\n\n'+note).encode('utf-8'))
    assert all(repair_sha in (ROOT/name).read_text(encoding='utf-8') for name in names)
    print(json.dumps(dict(closure_sha256=repair_sha,**closed)))


if __name__=='__main__': main()
