"""Track actual third capacity simulation; source and prior attempts stay unchanged."""
import json
import shutil
from pathlib import Path
from datetime import datetime, timezone
from measurement import sha256,write_json,exclusive_lock
root=Path(__file__).resolve().parents[2]; base=root/'deployment/mage_vl4b/optimization_v1'
gate=base/'gates/G02-decode-one-occupancy/attempt_03'
if gate.exists(): raise RuntimeError('Attempt03 exists')
prep=root/'tmp/op01_decode_one_occupancy_v3/PREPARATION.json'
smoke=root/'tmp/op01_ready_driver_recovery/xsim.log'
manifest=json.loads(prep.read_text())
if sha256(smoke)!=manifest['injection_smoke_sha256']: raise RuntimeError('Smoke identity mismatch')
record=dict(status='RUNNING_NOT_PASS',session_id=53417,build_id='0x4F503131',
    preparation=prep.relative_to(root).as_posix(),preparation_sha256=sha256(prep),
    recovery_smoke_sha256=sha256(smoke),board_deployed=False,performance_pass=False,
    next_action='Poll53417; no restart on observation timeout. Require full256cycle holds, four peaks,4/4 and frozen outputs before terminal collection.')
note='''## FIFO attempt03已启动（2026-09-25）

当前唯一会话53417，隔离tmp/op01_decode_one_occupancy_v3。共享ready在非采样沿release并恢复pending请求；短XSIM已覆盖实际VIP单次赋值/等待语义。
增加100000周期心跳：start/finish/四FIFO当前占用/ready/仿真时间，另设未启动预算。原容量8192、保持256cycle、两模式4事务及输出冻结比较不变。
旧81342已终止且记录ABORTED_TESTBENCH_RELEASE_DEFECT；不得恢复。计算核/综合/已过CSim不变；尚未PASS，不进入整壳/板端。
通过后使用record_decode_one_occupancy_v2.py（已指向attempt03）收集终态，执行backup_evidence.py；之后prepare_decode_one_ip_export.py才允许创建独立导出副本。

'''
with exclusive_lock(base/'evidence.lock'):
    gate.mkdir(parents=True); shutil.copyfile(smoke,gate/'ready_driver_recovery_smoke.log')
    write_json(gate/'RUN_STATE.json',record)
    p=base/'STATE.json'; state=json.loads(p.read_text(encoding='utf-8-sig'))
    state['decode_one_active_session']=53417
    state['results']['decode_one_occupancy_active']=(gate/'RUN_STATE.json').relative_to(root).as_posix()
    state['next_action']=record['next_action']; state['updated_utc']=datetime.now(timezone.utc).isoformat(); write_json(p,state)
    p=root/'deployment/mage_vl4b/BOARD_GATE_RESULT.json'; state=json.loads(p.read_text(encoding='utf-8-sig')); state['latest_decode_one_occupancy']=record; write_json(p,state)
    for p in [root/'CURRENT_STATE.md',root/'docsMILESTONES.md',base/'NEXT_ACTION.md',base/'reports/DECODE_ONE_FIFO_COVERAGE.md']:
        old=p.read_bytes(); split=old.find(b'\n')+1; temp=p.with_suffix(p.suffix+'.start03.partial')
        if temp.exists(): raise RuntimeError('Pending update')
        temp.write_bytes(old[:split]+b'\n'+note.encode()+old[split:]); temp.replace(p)
print('ATTEMPT03_TRACKED_NOT_PASS')
