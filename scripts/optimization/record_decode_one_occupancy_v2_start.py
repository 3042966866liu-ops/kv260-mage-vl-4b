"""Freeze smoke evidence and track the independently launched attempt02 (not PASS)."""
import json
import shutil
from datetime import datetime, timezone
from pathlib import Path
from measurement import exclusive_lock, sha256, write_json

root = Path(__file__).resolve().parents[2]
base = root/'deployment/mage_vl4b/optimization_v1'
gate = base/'gates/G02-decode-one-occupancy/attempt_02'
if gate.exists():
    raise RuntimeError('Refuse existing attempt02 tracking')
smoke = root/'tmp/op01_ready_injection_smoke/xsim.log'
if 'SHARED_READY_SMOKE_PASS blocked_cycles=256 recovered_transfers=32 mismatches=0' not in smoke.read_text():
    raise RuntimeError('Smoke evidence absent')
prep = root/'tmp/op01_decode_one_occupancy_v2/PREPARATION.json'
manifest = json.loads(prep.read_text())
if sha256(smoke) != manifest['injection_smoke_sha256']:
    raise RuntimeError('Smoke identity changed')
gate.mkdir(parents=True)
shutil.copyfile(smoke, gate/'ready_injection_smoke.log')
record = dict(status='RUNNING_NOT_PASS', session_id=81342, build_id='0x4F503131',
    preparation=prep.relative_to(root).as_posix(), preparation_sha256=sha256(prep),
    smoke_sha256=sha256(smoke), board_deployed=False, performance_pass=False,
    prior_failed_attempt='gates/G02-decode-one-occupancy/attempt_01/result.json',
    next_action='Poll existing session81342; require both full/256cycle hold markers, 4/4, no errors and five frozen output hashes. Do not restart on observation timeout.')
note = '''## Decode-one FIFO专项attempt02已启动，旧握手错误已隔离（2026-09-25）

原attempt01为FAIL_TESTBENCH_HANDSHAKE_INJECTION，完整失败保留；不是DUT数值失败。
短XSIM复现旧法dut0/monitor32，新共享ready阻塞256周期后恢复32次，两端计数一致。
新隔离tmp/op01_decode_one_occupancy_v2，session81342；只重编测试台，不重跑HLS综合/CSim，不改核。
新增共享ready相等断言、分片3满8192持续256cycle断言、每事务完成时间及四FIFO累计峰值。
当前RUNNING_NOT_PASS，先收这轮容量/冻结输出结果，未授权进入整壳或板端。旧下文会话均为历史，不可据其重启。
证据gates/G02-decode-one-occupancy/attempt_02/RUN_STATE.json；连续descriptor排空见OP01-descriptor-serialization静态分析，非10×512实测。

'''
with exclusive_lock(base/'evidence.lock'):
    write_json(gate/'RUN_STATE.json', record)
    p=base/'STATE.json'; state=json.loads(p.read_text(encoding='utf-8-sig'))
    state['results']['decode_one_occupancy_failure']='deployment/mage_vl4b/optimization_v1/gates/G02-decode-one-occupancy/attempt_01/result.json'
    state['results']['decode_one_occupancy_active']=(gate/'RUN_STATE.json').relative_to(root).as_posix()
    state['decode_one_active_session']=81342
    state['updated_utc']=datetime.now(timezone.utc).isoformat()
    state['next_action']=record['next_action']
    write_json(p,state)
    p=root/'deployment/mage_vl4b/BOARD_GATE_RESULT.json'; state=json.loads(p.read_text(encoding='utf-8-sig'))
    state['latest_decode_one_occupancy']=record
    write_json(p,state)
    for p in [root/'CURRENT_STATE.md',root/'docsMILESTONES.md',base/'NEXT_ACTION.md']:
        old=p.read_bytes(); split=old.find(b'\n')+1
        temp=p.with_suffix(p.suffix+'.occupancy02.partial')
        if temp.exists(): raise RuntimeError('Pending documentation update')
        temp.write_bytes(old[:split]+b'\n'+note.encode()+old[split:]); temp.replace(p)
print('OCCUPANCY_ATTEMPT02_TRACKED_NOT_PASS')
