"""Collect terminal attempt03 only; never infer PASS from an active log."""
import argparse
import json
import shutil
from datetime import datetime, timezone
from pathlib import Path
from check_decode_one_occupancy_v2 import audit, ROOT, STAGE
from measurement import exclusive_lock, sha256, write_json

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--terminal-exit-code',type=int,required=True)
    parser.add_argument('--terminal-evidence',required=True,
                        help='Observed terminal tool chunk/session reference, not a predicted exit')
    args=parser.parse_args()
    if args.terminal_exit_code != 0:
        raise RuntimeError('Nonzero terminal exit: preserve failure, do not collect PASS')
    base=ROOT/'deployment/mage_vl4b/optimization_v1'
    gate=base/'gates/G02-decode-one-occupancy/attempt_03'
    out=gate/'result.json'
    if out.exists(): raise RuntimeError('Immutable terminal result exists')
    result=audit()
    result.update(status='PASS_CAPACITY_BACKPRESSURE_RTL_ONLY',build_id='0x4F503131',
        terminal_evidence=args.terminal_evidence,terminal_exit_code=0,
        board_deployed=False,performance_pass=False,
        continuous_descriptor_evidence='runs/OP01-descriptor-serialization/result.json',
        maximum_rows_times_descriptors_simulated=False,
        limits=['Not formal proof', 'Not full shell, board, performance or complete model quality acceptance'])
    report=base/'reports/DECODE_ONE_FIFO_COVERAGE.md'
    old=report.read_bytes()
    rows='\n'.join(f'| {name} | {i} | 8192 | 8192（单descriptor推导） | {p} | PASS |'
        for i,(name,p) in enumerate(zip(['result_U','result_1_U','result_2_U','result_3_U'],result['peaks'])))
    times='\n'.join(f"- {m['mode']}：满容量保持{m['hold_cycles']}周期；释放到事务完成{m['release_to_completion_ps']} ps（仿真时间，非实板时延）。"
        for m in result['modes'])
    text=f'''# Decode-one 结果FIFO逐项覆盖报告

## attempt03终态：PASS_CAPACITY_BACKPRESSURE_RTL_ONLY

候选Build0x4F503131；共享ready注入，DUT未改。4/4事务完成，两种模式均触及分片3容量8192并保持256周期。
五份输出（数据、keep、strb、last、返回码）的SHA与正常RTL冻结结果一致；无Fatal/UVM_ERROR/UVM_FATAL。

| FIFO实例 | 分片 | 配置深度 | 生产上界 | 全程实测峰值 | 此专项 |
|---|---:|---:|---|---:|---|
{rows}

单位为32-bit FIFO word；不要求所有FIFO都满，不用推导值替代实测。
以上为四事务全程峰值，并非按模式拆分的峰值。日志中每事务峰值是截至当时的累计峰值。

{times}

## 覆盖与边界

- T32及Decode-one：groups1/W4，rows512×1 descriptor，容量阻塞/释放；rows8×10 descriptor，正常随机回压。
- groups152/W2、groups152/W4、rows384尾块由独立补充RTL门覆盖；不能把不同场景组合宣称为最大几何组合RTL实测。
- 连续descriptor排空结论来自精确生成RTL：顶层等当前ready和merge.done；merge消费完本轮全部结果后才完成。静态分析见runs/OP01-descriptor-serialization/result.json；不是形式化证明或10×512实测。
- 原attempt01握手分裂、attempt02的release恢复遗漏均保留。第三轮使用实际驱动语义短测验证的恢复方式。

## 证据

- gates/G02-decode-one-occupancy/attempt_03/result.json
- tmp/op01_decode_one_occupancy_v3/PREPARATION.json及verilog/xsim.log（仓库根目录下）
- gates/G02-decode-one-occupancy/attempt_03/report_before_terminal.md保留旧报告。

下一步核对门禁闭包并准备独立IP/整壳候选。尚未进入实板，不证明Decode速度、L1/L2/L3或G08通过。
'''
    note=f'''## Decode-one FIFO容量专项attempt03通过（2026-09-25）

Build0x4F503131，4/4完成；四FIFO实测峰值{result['peaks']}（深度均8192，单位32bitword）。
两种模式分片3满8192保持256cycle，释放后完成；5份输出SHA与正常RTL冻结结果一致。
证据gates/G02-decode-one-occupancy/attempt_03/result.json。原握手错误及恢复遗漏记录保留；不重跑通过的数值/综合。
连续descriptor结论仍为精确RTL静态排空分析，非10×512实测。下一步门禁闭包/独立IP与整壳，不是直接上板或性能PASS。

'''
    with exclusive_lock(base/'evidence.lock'):
        prior=gate/'report_before_terminal.md'
        if prior.exists(): raise RuntimeError('Prior report already archived')
        prior.write_bytes(old)
        write_json(out,result)
        report_tmp=report.with_suffix('.md.terminal.partial')
        if report_tmp.exists(): raise RuntimeError('Pending report update')
        report_tmp.write_text(text,encoding='utf-8'); report_tmp.replace(report)
        p=base/'STATE.json'; state=json.loads(p.read_text(encoding='utf-8-sig'))
        state['results']['decode_one_occupancy']=out.relative_to(ROOT).as_posix()
        state['decode_one_active_session']=None
        state['next_action']='Audit complete offline gate identities; prepare isolated IP/full-shell candidate. No board/performance promotion.'
        state['updated_utc']=datetime.now(timezone.utc).isoformat(); write_json(p,state)
        p=ROOT/'deployment/mage_vl4b/BOARD_GATE_RESULT.json'; state=json.loads(p.read_text(encoding='utf-8-sig'))
        state['latest_decode_one_occupancy']=dict(status=result['status'],result=out.relative_to(ROOT).as_posix(),
            sha256=sha256(out),board_deployed=False,performance_pass=False)
        write_json(p,state)
        run=json.loads((gate/'RUN_STATE.json').read_text()); run.update(status=result['status'],
            terminal_result='result.json',next_action='Do not restart completed attempt03')
        write_json(gate/'RUN_STATE.json',run)
        for p in [ROOT/'CURRENT_STATE.md',ROOT/'docsMILESTONES.md',base/'NEXT_ACTION.md']:
            old=p.read_bytes(); split=old.find(b'\n')+1
            temp=p.with_suffix(p.suffix+'.occupancy-terminal.partial')
            if temp.exists(): raise RuntimeError('Pending document update')
            temp.write_bytes(old[:split]+b'\n'+note.encode()+old[split:]); temp.replace(p)
    print(json.dumps(result,indent=2))

if __name__=='__main__': main()
