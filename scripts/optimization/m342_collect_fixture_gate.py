"""Atomic exact-byte evidence then synchronized state after EACH gate level."""
import base64
import hashlib
import json
import os
from pathlib import Path
import re
import sys
ROOT=Path(__file__).resolve().parents[2]


def atomic(path,data):
    part=path.with_name(path.name+'.m342-part');part.write_bytes(data);os.replace(part,path)


def main():
    level=sys.argv[1]
    if level not in ('single-descriptor','single-chain'):raise ValueError(level)
    log=(ROOT/f'tmp/m342/{level}_uart.log').read_text(encoding='utf-8-sig')
    expected=re.search(r'M342_RESULT_SHA256=([0-9a-f]{64})',log).group(1)
    data=base64.b64decode(re.search(r'M342_RESULT_BASE64=([A-Za-z0-9+/=]+)',log).group(1),validate=True)
    if hashlib.sha256(data).hexdigest()!=expected:raise RuntimeError('Board result hash mismatch')
    result=json.loads(data)
    if result['gate_level']!=level:raise RuntimeError('Gate identity mismatch')
    if result['status']=='PASS' and (f'M342_FIXTURE_DONE level={level} gate_rc=0' not in log or result['unsafe_buffers_retained']):
        raise RuntimeError('Cannot publish PASS without runner completion and safe release')
    run=ROOT/f'deployment/mage_vl4b/optimization_v1/runs/M342-{level}-board-01';run.mkdir(parents=True,exist_ok=True)
    if (run/'BOARD_RESULT.json').exists() and (run/'BOARD_RESULT.json').read_bytes()!=data:
        raise RuntimeError('Refusing to overwrite different evidence')
    atomic(run/'BOARD_RESULT.json',data)
    for name in ('CURRENT_STATE.md','docsMILESTONES.md','deployment/mage_vl4b/BOARD_GATE_RESULT.json'):
        backup=run/(Path(name).name+'.before')
        if not backup.exists():backup.write_bytes((ROOT/name).read_bytes())
    board_path=ROOT/'deployment/mage_vl4b/BOARD_GATE_RESULT.json';board=json.loads(board_path.read_text(encoding='utf-8-sig'))
    board['latest_m342_'+level.replace('-','_')]=dict(status=result['status'],evidence_level='L4_MINIMAL_ONLY',build_id=result['build_id'],
        result=(run/'BOARD_RESULT.json').relative_to(ROOT).as_posix(),sha256=expected,prefetch_candidate_executed=result['prefetch_candidate_executed'],performance_pass=False)
    atomic(board_path,(json.dumps(board,ensure_ascii=False,indent=2)+'\n').encode())
    note=('## M342 '+level+' '+result['status']+'（2026-10-01）\n\n'
          '原稳定Build `0x4D395832`，隔离13载荷/83,548B包manifest `b97d995bfa2f9afecd3e324c1b823731245d5c090fc1bb6de43919fc4db11e96`；'
          '同COM3包/源码/前级结果哈希、root/XRT/PYNQ/M175清单环境门禁，复用严格同SHA的稳定数值CSim/header/RTL/bitstream证据。'
          '采用原M128真实权重、独立golden与冻结M157 FP16非正规数转带符号零契约，其余位及padding精确；没有新容差。'
          '结果 `'+(run/'BOARD_RESULT.json').relative_to(ROOT).as_posix()+'` SHA `'+expected+'`，状态 `'+result['status']+'`，错误 `'+json.dumps(result['errors'])+'`。'+
          ('仅单descriptor，未执行预取候选。' if level=='single-descriptor' else '一个基线单链后，M340后台原复制/同步函数预取真实权重、最大26.5625MiB额外CMA bank，执行A→B→A三次双descriptor单chain；每次独立golden/缓冲SHA/计数/地址与安全释放情况见JSON。')+
          '仅L4最小门禁，不是单layer、固定文本、完整159视频、性能或Web部署/晋级。稳定源/回滚/boot/DTB/CMA配置未改。'
          '下一步 '+result['next_step']+'；失败仅留在此级，不重跑完整模型。\n\n')
    for name in ('CURRENT_STATE.md','docsMILESTONES.md'):
        path=ROOT/name;heading,rest=path.read_text(encoding='utf-8-sig').split('\n',1)
        atomic(path,(heading+'\n\n'+note+rest.lstrip('\n')).encode())
    print(json.dumps(dict(status=result['status'],level=level,result_sha256=expected,errors=result['errors'],transactions=len(result['transactions']),prefetch=result.get('prefetch'))))


if __name__=='__main__':main()
