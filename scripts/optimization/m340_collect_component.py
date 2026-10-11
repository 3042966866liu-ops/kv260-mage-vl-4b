"""Recover exact CPU-only result bytes and synchronize authoritative records."""
import base64
import hashlib
import json
import os
from pathlib import Path
import re
ROOT=Path(__file__).resolve().parents[2]


def atomic(path,data):
    part=path.with_name(path.name+'.m340-part');part.write_bytes(data);os.replace(part,path)


def main():
    log=(ROOT/'tmp/m340/component_uart.log').read_text(encoding='utf-8-sig')
    if 'M340_CPU_ONLY_DONE gate_rc=0' not in log or '__M75C_UART_RC_0__' not in log:
        raise RuntimeError('Runner did not complete')
    expected=re.search(r'M340_RESULT_SHA256=([0-9a-f]{64})',log).group(1)
    data=base64.b64decode(re.search(r'M340_RESULT_BASE64=([A-Za-z0-9+/=]+)',log).group(1),validate=True)
    if hashlib.sha256(data).hexdigest()!=expected: raise RuntimeError('Board result hash mismatch')
    result=json.loads(data)
    run=ROOT/'deployment/mage_vl4b/optimization_v1/runs/M340-component-board-python-01'
    run.mkdir(parents=True,exist_ok=False)
    atomic(run/'BOARD_RESULT.json',data)
    for name in ('CURRENT_STATE.md','docsMILESTONES.md','deployment/mage_vl4b/BOARD_GATE_RESULT.json'):
        (run/(Path(name).name+'.before')).write_bytes((ROOT/name).read_bytes())
    board_path=ROOT/'deployment/mage_vl4b/BOARD_GATE_RESULT.json'
    board=json.loads(board_path.read_text(encoding='utf-8-sig'))
    board['latest_m340_board_cpu_component']=dict(status=result['status'],evidence_level='L0',result=(run/'BOARD_RESULT.json').relative_to(ROOT).as_posix(),
        sha256=expected,overlay_loaded=False,hardware_gate_run=False,performance_pass=False,
        cma_free_idle_bytes=result.get('memory_bytes',{}).get('CmaFree'))
    atomic(board_path,(json.dumps(board,ensure_ascii=False,indent=2)+'\n').encode())
    note=('## M340 板端 Python 组件与 CMA 快照（2026-10-01）\n\n'
          '独立包6载荷/21,792B、manifest `8d9d0123d40de0fb7b070a690bab3b65429dbad71c29ddce288d44b6bdfad50a`，COM3逐文件哈希、Bash语法和PYNQ Python3.10.12十项CPU组件测试完成，状态 `'+result['status']+'`，仅L0。'
          '没有加载overlay、实例化DMA、分配CMA或运行候选FPGA。原始结果 `'+(run/'BOARD_RESULT.json').relative_to(ROOT).as_posix()+'` SHA `'+expected+'`。'
          '空闲CmaTotal=838,860,800B，CmaFree=452,452,352B（431.492MiB），第二四缓冲组需27,852,800B（26.5625MiB）及64MiB预留，快照前提满足；必须真实runtime分配后重新检查，不能据此宣称完整请求内存已通过。'
          '板端墙钟未同步（原始Unix时间保留，不作为日期排序依据）；性能计时采用monotonic。稳定Build `0x4D395832`、回滚/boot/DTB/CMA配置不变。'
          '下一步准备M341最小门禁闭包，复用严格身份相同的稳定CSim/header/RTL容量背压证据，按Build-ID-only→单descriptor→双缓冲单chain数值/计数与安全释放→单layer→固定文本→固定159视频/交错A/B逐级推进，失败不越级；不宣称提速或晋级。\n\n')
    for name in ('CURRENT_STATE.md','docsMILESTONES.md'):
        path=ROOT/name;heading,rest=path.read_text(encoding='utf-8-sig').split('\n',1)
        atomic(path,(heading+'\n\n'+note+rest.lstrip('\n')).encode())
    print(json.dumps(dict(status=result['status'],tests=result['tests_run'],memory_bytes=result['memory_bytes'],evidence=str(run))))


if __name__=='__main__':main()
