"""Synchronize exact COM3 Build-ID evidence before allowing any next level."""
import base64
import hashlib
import json
import os
from pathlib import Path
import re
ROOT=Path(__file__).resolve().parents[2]


def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()


def atomic(path,data):
    part=path.with_name(path.name+'.m341-part');part.write_bytes(data);os.replace(part,path)


def main():
    log=(ROOT/'tmp/m341/build_gate_uart.log').read_text(encoding='utf-8-sig')
    expected=re.search(r'M341_RESULT_SHA256=([0-9a-f]{64})',log).group(1)
    data=base64.b64decode(re.search(r'M341_RESULT_BASE64=([A-Za-z0-9+/=]+)',log).group(1),validate=True)
    if hashlib.sha256(data).hexdigest()!=expected:raise RuntimeError('Result bytes do not match board hash')
    result=json.loads(data)
    if result['status']=='PASS' and ('M341_BUILD_ID_DONE gate_rc=0' not in log or result['unsafe_dma_buffers_retained']):
        raise RuntimeError('PASS without safe release/completed runner')
    run=ROOT/'deployment/mage_vl4b/optimization_v1/runs/M341-build-id-board-01';run.mkdir(parents=True,exist_ok=False)
    atomic(run/'BOARD_RESULT.json',data)
    for name in ('CURRENT_STATE.md','docsMILESTONES.md','deployment/mage_vl4b/BOARD_GATE_RESULT.json'):
        (run/(Path(name).name+'.before')).write_bytes((ROOT/name).read_bytes())
    board_path=ROOT/'deployment/mage_vl4b/BOARD_GATE_RESULT.json';board=json.loads(board_path.read_text(encoding='utf-8-sig'))
    board['latest_m341_build_id_board_gate']=dict(status=result['status'],gate_level='Build-ID-only',evidence_level='L4_BUILD_ID_ONLY',build_id=result.get('build_id'),
        result=(run/'BOARD_RESULT.json').relative_to(ROOT).as_posix(),sha256=expected,prefetch_candidate_executed=False,performance_pass=False)
    atomic(board_path,(json.dumps(board,ensure_ascii=False,indent=2)+'\n').encode())
    note=('## M341 COM3 Build-ID-only 门禁 '+result['status']+'（2026-10-01）\n\n'
          '用户续期后，独立8载荷/49,351B包manifest `fe7f43cf3dcce33fba86fdd33259f35fc5c7066b9bf9d58acccaac84a622b852` 经COM3逐文件SHA、Bash语法、同COM3 sudo及固定root/XRT/PYNQ/xclbinutil/M175清单环境门禁后执行稳定零数据最小事务及同bitstream rollback零事务。'
          '原始结果 `'+(run/'BOARD_RESULT.json').relative_to(ROOT).as_posix()+'` SHA `'+expected+'`，状态 `'+result['status']+'`。'
          '仅Build-ID-only级，未执行M340权重预取候选、真实descriptor/chain、layer、模型或性能验收。'
          'snapshot/安全释放/boot与cmdline保护情况均以JSON为准；无boot/DTB/CMA/分区或稳定源修改。'
          '历史sudo过期与首轮仿真日志追加导致哈希拒绝均保留，未重复完整模型。下一步 '+
          ('单descriptor固定FP16-FTZ数值门禁，同步后才做双缓冲单chain位精确及安全门禁。' if result['status']=='PASS' else '只诊断此级，失败未解除前不进入更大门禁。')+'\n\n')
    for name in ('CURRENT_STATE.md','docsMILESTONES.md'):
        path=ROOT/name;heading,rest=path.read_text(encoding='utf-8-sig').split('\n',1)
        atomic(path,(heading+'\n\n'+note+rest.lstrip('\n')).encode())
    print(json.dumps(dict(status=result['status'],build_id=result.get('build_id'),errors=result['errors'],evidence=str(run))))


if __name__=='__main__':main()
