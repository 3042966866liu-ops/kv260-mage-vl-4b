"""Preserve attempt02 abort caused by independently proven release semantics."""
import json
import shutil
from pathlib import Path
from datetime import datetime, timezone
from measurement import sha256, write_json, exclusive_lock
root=Path(__file__).resolve().parents[2]
base=root/'deployment/mage_vl4b/optimization_v1'
gate=base/'gates/G02-decode-one-occupancy/attempt_02'
out=gate/'result.json'
if out.exists(): raise RuntimeError('Immutable result exists')
smoke=root/'tmp/op01_ready_driver_recovery/xsim.log'
text=smoke.read_text(errors='replace')
for marker in ['RELEASE_ONLY_STALL_REPRODUCED transfers=0 ready=0','VIP_DRIVER_RECOVERY_PASS transfers=32 mismatches=0']:
    if marker not in text: raise RuntimeError('Missing recovery proof')
paths=[smoke,root/'hls/mage_decode_op01_one/tb_ready_driver_recovery.sv',
       root/'tmp/op01_decode_one_occupancy_v2/verilog/xsim.log',
       root/'tmp/op01_decode_one_occupancy_v2/verilog/op01_decode_one_kernel.autotb.v',
       root/'tmp/op01_decode_one_occupancy_v2/verilog/svr/svr_slave_driver.sv']
result=dict(status='ABORTED_TESTBENCH_RELEASE_DEFECT',session_id=81342,
    terminal_exit_code=1,terminal_evidence='write_stdin chunk b92546 after identity-checked stop of PID17488',
    build_id='0x4F503131',board_deployed=False,performance_pass=False,dut_failure_proven=False,
    observed_in_capacity_run='No full/completion marker before intentional stop; no claim that release had already occurred',
    cause='VIP driver assigns ready once then waits. Verilog release of a forced variable retains zero until reassigned. Prior smoke incorrectly used periodic ready assignments.',
    corrected_smoke='Explicit restore of pending ready request at non-sampling edge:32 transfers,0 mismatches',
    peaks=None,evidence={p.relative_to(root).as_posix():sha256(p) for p in paths})
note='''## FIFO attempt02已主动终止：短测证实release恢复遗漏（2026-09-25）

81342终态outer rc1，核对PID17488与启动时间后停止。不是因日志静默判挂死，而是新短XSIM证明实际VIP驱动只写一次ready；release后保留0，无后续赋值时无法恢复。
此前短测每周期重写ready，未覆盖真实驱动语义；此为测试台验证遗漏，非DUT故障。容量运行停止前尚无满容量/完成标志，不声称它已在release处停住。
原attempt02完整日志/result.json保留；新短测显式恢复pending ready后32传输/0握手差异通过。
下一步独立attempt03增加release后的ready恢复，保持256cycle与全部原验收条件；不重跑数值/HLS，不上板。

'''
with exclusive_lock(base/'evidence.lock'):
    shutil.copyfile(smoke,gate/'ready_driver_recovery_smoke.log')
    write_json(out,result)
    p=gate/'RUN_STATE.json'; run=json.loads(p.read_text()); run.update(status=result['status'],terminal_result='result.json',next_action='Prepare isolated attempt03; do not resume81342'); write_json(p,run)
    p=base/'STATE.json'; state=json.loads(p.read_text(encoding='utf-8-sig')); state['decode_one_active_session']=None
    state['results']['decode_one_occupancy']=out.relative_to(root).as_posix()
    state['next_action']='Prepare attempt03 with verified shared-ready release restoration; preserve attempt02 abort.'
    state['updated_utc']=datetime.now(timezone.utc).isoformat(); write_json(p,state)
    p=root/'deployment/mage_vl4b/BOARD_GATE_RESULT.json'; state=json.loads(p.read_text(encoding='utf-8-sig'))
    state['latest_decode_one_occupancy']=dict(status=result['status'],result=out.relative_to(root).as_posix(),sha256=sha256(out),board_deployed=False,performance_pass=False); write_json(p,state)
    for p in [root/'CURRENT_STATE.md',root/'docsMILESTONES.md',base/'NEXT_ACTION.md',base/'reports/DECODE_ONE_FIFO_COVERAGE.md']:
        old=p.read_bytes(); split=old.find(b'\n')+1; temp=p.with_suffix(p.suffix+'.abort02.partial')
        if temp.exists(): raise RuntimeError('Pending update')
        temp.write_bytes(old[:split]+b'\n'+note.encode()+old[split:]); temp.replace(p)
print(result['status'])
