"""Record and prevent the collector-return-value operational error."""
import hashlib
import json
import os
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
RUN=ROOT/'deployment/mage_vl4b/optimization_v1/runs/M342-control-repair-01'


def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()


def atomic(path,data):
    part=path.with_name(path.name+'.m342-part');part.write_bytes(data);os.replace(part,path)


def main():
    if RUN.exists():raise RuntimeError('Immutable repair record exists')
    RUN.mkdir(parents=True)
    for name in ('CURRENT_STATE.md','docsMILESTONES.md','DEPLOYMENT_OPERATION_MISTAKES_REVIEW.md','deployment/mage_vl4b/BOARD_GATE_RESULT.json'):
        (ROOT/name).read_text(encoding='utf-8-sig')
        (RUN/(Path(name).name+'.before')).write_bytes((ROOT/name).read_bytes())
    result=dict(status='FIXED_COLLECTOR_AND_FAIL_CLOSED_ADVANCE_GUARD',
        actual_error='Collector note missed + before parenthesized conditional; raw result and BOARD JSON had been written but two Markdown records were not synchronized',
        control_error='The orchestration batch did not inspect collector exit1 before invoking the next single-chain gate. Descriptor hardware PASS and board hash prerequisite were valid, but host synchronization order was violated',
        recovery='Corrected collector, replayed exact existing bytes without hardware rerun; all three records now synchronized for descriptor and chain. Original before copies preserved',
        prevention='Versioned m342_run_and_collect.ps1 checks previous exact evidence hash in BOARD/CURRENT_STATE/docsMILESTONES; captures collector exit code; nonzero forbids advancing and only collection repair is allowed',
        workflow_sha256=sha(ROOT/'scripts/optimization/m342_run_and_collect.ps1'),
        hardware_repeated=False,full_e2e_run=False,performance_pass=False,
        descriptor_result_sha256='f28fbdf08aa2527d932f00c0b0b17182a4d0db7254423f486fcc8c202e81856e',
        chain_result_sha256='6fcc267aab9fdebbc3641a921d6518c9c266f31a9b7a515972dc30d9fa948aea')
    atomic(RUN/'RESULT.json',(json.dumps(result,indent=2)+'\n').encode())
    review=ROOT/'DEPLOYMENT_OPERATION_MISTAKES_REVIEW.md'
    entry=('\n## M342 证据同步返回值必须阻止后级门禁（2026-10-01）\n\n'
           '- 单descriptor硬件已PASS，但收集器Markdown拼接缺少加号；原始结果和BOARD JSON已落盘，两份状态文档尚未同步。控制编排未检查收集器exit=1，提前启动了后级单chain，违反先同步后推进顺序。不是FPGA数值失败，也没有执行完整模型。\n'
           '- 修复收集器并复用同SHA板端字节完成三份记录同步，未重跑硬件；旧before证据保留。\n'
           '- 强制规则：任何依赖门禁和证据同步的后续调用必须读取前一步返回值。只有raw evidence SHA、BOARD字段及CURRENT_STATE/docsMILESTONES均已同步才可解锁后级；收集器失败只重做回收/同步，不重复硬件。\n'
           '- 新控制器 `scripts/optimization/m342_run_and_collect.ps1` 在调用前核对三份记录的精确前级SHA，在调用后捕获收集器退出码；失败即停止。证据 `deployment/mage_vl4b/optimization_v1/runs/M342-control-repair-01/RESULT.json`。\n')
    atomic(review,(review.read_text(encoding='utf-8-sig').rstrip()+'\n'+entry).encode())
    boardpath=ROOT/'deployment/mage_vl4b/BOARD_GATE_RESULT.json';board=json.loads(boardpath.read_text(encoding='utf-8-sig'))
    board['latest_m342_control_repair']=dict(status=result['status'],result=(RUN/'RESULT.json').relative_to(ROOT).as_posix(),sha256=sha(RUN/'RESULT.json'),hardware_repeated=False)
    atomic(boardpath,(json.dumps(board,ensure_ascii=False,indent=2)+'\n').encode())
    note=('## M342 收集器与推进检查修复（2026-10-01）\n\n'
          '单descriptor已PASS，但收集器Markdown拼接失败；编排未检查exit1而提前启动单chain，违反先同步后推进。已明确记录在操作复盘；修复后复用原始SHA字节，三份权威记录均同步，未重跑FPGA。'
          '新增控制器在推进前检查前级SHA在BOARD/CURRENT_STATE/docsMILESTONES三份记录中一致，收集器非零立即停止，仅修复收集。'
          '修复证据 `'+(RUN/'RESULT.json').relative_to(ROOT).as_posix()+'` SHA `'+sha(RUN/'RESULT.json')+'`。'
          'M342双缓冲单chain结果仍为PASS `6fcc267aab9fdebbc3641a921d6518c9c266f31a9b7a515972dc30d9fa948aea`，仅L4；稳定Build/回滚/boot/DTB/CMA不变，无完整请求提速结论。'
          '下一步独立单layer数值门禁；必须先完成证据同步检查，不重复已完成最小门禁。\n\n')
    for name in ('CURRENT_STATE.md','docsMILESTONES.md'):
        path=ROOT/name;heading,rest=path.read_text(encoding='utf-8-sig').split('\n',1)
        atomic(path,(heading+'\n\n'+note+rest.lstrip('\n')).encode())
    print(json.dumps(dict(status=result['status'],result_sha256=sha(RUN/'RESULT.json'))))


if __name__=='__main__':main()
