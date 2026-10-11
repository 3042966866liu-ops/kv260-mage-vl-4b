"""Persist an operator-aborted test without turning partial coverage into PASS."""
import json
from pathlib import Path
from datetime import datetime, timezone
from measurement import sha256, write_json, exclusive_lock

root = Path(__file__).resolve().parents[2]
base = root / 'deployment/mage_vl4b/optimization_v1'
gate = base / 'gates/G02-decode-one-occupancy/attempt_03'
stop = json.loads((gate / 'USER_STOP.json').read_text())
assert stop['status'] == 'STOPPED_BY_USER_NOT_PASS'
log = root / 'tmp/op01_decode_one_occupancy_v3/verilog/xsim.log'
assert 'Exiting xsim' in log.read_text(errors='replace')
record = dict(stop, build_id='0x4F503131', log_sha256=sha256(log),
              board_deployed=False, performance_pass=False,
              next_action='Prepare isolated experimental implementation under user instruction; capacity gate remains incomplete. No rerun, no stable promotion.')
note = '''## FIFO attempt03按用户要求中止（2026-09-25，覆盖下方运行中记录）

session53417已退出rc1，PID5656已确认停止；不是DUT失败，也不是容量PASS。
完成2/4事务；停止前最后心跳2700000，四FIFO当前占用8190/8192/8192/4608。
原始日志及USER_STOP.json保留；十分钟监控已停用。不得重新轮询或重启旧会话。
用户要求停止长测并推进上板：下一步准备隔离实验构建，明确容量专项未完成，不授予正式RTL完整覆盖或性能晋级。
尚无新bitstream；先导出/整壳资源时序，再Build-ID及最小事务。稳定boot/DTB/CMA/overlay不变。

'''
with exclusive_lock(base / 'evidence.lock'):
    result = gate / 'result.json'
    if result.exists():
        raise RuntimeError('Refuse replacing terminal evidence')
    write_json(result, record)
    p = gate / 'RUN_STATE.json'
    write_json(gate / 'RUN_STATE_BEFORE_USER_STOP.json', json.loads(p.read_text()))
    write_json(p, record)
    p = base / 'STATE.json'
    state = json.loads(p.read_text(encoding='utf-8-sig'))
    state['decode_one_active_session'] = None
    state['results']['decode_one_occupancy_terminal'] = result.relative_to(root).as_posix()
    state['next_action'] = record['next_action']
    state['updated_utc'] = datetime.now(timezone.utc).isoformat()
    write_json(p, state)
    p = root / 'deployment/mage_vl4b/BOARD_GATE_RESULT.json'
    state = json.loads(p.read_text(encoding='utf-8-sig'))
    state['latest_decode_one_occupancy'] = record
    write_json(p, state)
    for p in [root/'CURRENT_STATE.md', root/'docsMILESTONES.md', base/'NEXT_ACTION.md', base/'reports/DECODE_ONE_FIFO_COVERAGE.md']:
        old = p.read_bytes()
        split = old.find(b'\n') + 1
        tmp = p.with_suffix(p.suffix + '.userstop.partial')
        if tmp.exists():
            raise RuntimeError('Pending state update')
        tmp.write_bytes(old[:split] + b'\n' + note.encode() + old[split:])
        tmp.replace(p)
print('USER_STOP_SYNCHRONIZED_NOT_PASS')
