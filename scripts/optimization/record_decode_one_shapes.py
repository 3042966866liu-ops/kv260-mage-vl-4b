"""Collect supplemental RTL evidence after terminal session68882 rc0 was observed."""
import json
from datetime import datetime, timezone
from pathlib import Path
from check_decode_one_shapes import audit, ROOT
from measurement import exclusive_lock, sha256, write_json

base = ROOT / 'deployment/mage_vl4b/optimization_v1'
out = base / 'gates/G02-decode-one-shapes/attempt_01/result.json'
if out.exists():
    raise RuntimeError('Immutable result exists; do not rerun')
result = audit()
result.update(status='PASS_SUPPLEMENTAL_RTL_COSIM_ONLY', build_id='0x4F503131',
              terminal_evidence=dict(session_id=68882, exit_code=0,
                  source='write_stdin terminal tool output chunk fedcc6, 2026-09-25',
                  final_postcheck='OP01_SHAPE_TRANSACTIONS_PASS', tool_exit=0),
              shapes=[dict(groups=152,bits=2,rows=8,words=512),
                      dict(groups=152,bits=4,rows=8,words=512),
                      dict(groups=1,bits=4,rows=384,words=24576)],
              limitations=['No board or performance result',
                           'No measured maximum FIFO occupancy; max-row normal RTL gate separate',
                           'Routed resource/timing and full-shell gates still required'],
              source_unchanged=True)
for name in ['decode_one.hpp','tb_rtl_shapes.cpp','resume_shapes_cosim.tcl']:
    p=ROOT/'hls/mage_decode_op01_one'/name
    result['evidence'][p.relative_to(ROOT).as_posix()]=sha256(p)
note = '''## Decode-one补充RTL正式通过（2026-09-25，覆盖旧会话状态）

- 原68882已退出rc0，3/3事务及最终C后检查PASS。groups152/W2、groups152/W4均rows8，以及groups1/W4/rows384尾块；word/TLAST/返回值与数值由testbench校验。
- gates/G02-decode-one-shapes/attempt_01/result.json；核SHA、原HLS综合及正常RTL报告SHA未变。没有重跑已通过的CSim/综合，旧77634中断日志保留。
- 尚无新板端部署、性能或路由时序结论。下一步先汇总覆盖与头文件身份，再生成隔离IP/整壳候选；不得运行会覆盖稳定目录的旧M134脚本。
- 正式结果收集后执行backup_evidence.py。所有L档和G08要求保持不变。

'''
with exclusive_lock(base/'evidence.lock'):
    write_json(out,result)
    p=base/'STATE.json'; state=json.loads(p.read_text(encoding='utf-8-sig'))
    state['results']['decode_one_shapes']=out.relative_to(ROOT).as_posix()
    state['updated_utc']=datetime.now(timezone.utc).isoformat()
    state['next_action']='Supplemental RTL complete; audit combined coverage/source closure, prepare isolated IP/full shell; no board promotion.'
    state['decode_one_active_session']=None
    write_json(p,state)
    p=ROOT/'deployment/mage_vl4b/BOARD_GATE_RESULT.json'
    state=json.loads(p.read_text(encoding='utf-8-sig'))
    state['latest_decode_one_shapes']=dict(status=result['status'], result=out.relative_to(ROOT).as_posix(),sha256=sha256(out),board_deployed=False,performance_pass=False)
    write_json(p,state)
    # Mechanical prepend preserves the complete prior history byte-for-byte.
    for p in [ROOT/'CURRENT_STATE.md', ROOT/'docsMILESTONES.md', base/'NEXT_ACTION.md']:
        old=p.read_bytes(); split=old.find(b'\n')+1
        tmp=p.with_suffix(p.suffix+'.shapes.partial')
        if tmp.exists(): raise RuntimeError('Unexpected pending documentation update')
        tmp.write_bytes(old[:split]+b'\n'+note.encode('utf-8')+old[split:])
        tmp.replace(p)
print(result['status'])
