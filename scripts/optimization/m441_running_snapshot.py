"""Immutable snapshot of an already started local RTL job; not a PASS."""
import json
import re
from m351_workflow import ROOT, BASE, atomic, encoded, sha, sync


def main():
    folder=BASE/'runs/M441-offline-continuation-01'
    start=folder/'START.json';s=json.loads(start.read_bytes())
    prep=folder/'PREPARATION.json';p=json.loads(prep.read_bytes())
    assert sha(prep)==s['preparation_sha256']
    assert not (folder/'RESULT.json').exists()
    progress=json.loads((folder/'PROGRESS.json').read_bytes())
    assert progress[-1]['status']=='WAITING_SAVED_ORIGINAL_CONTROLLERS'
    heartbeats=[]
    for variant in ('A','B'):
        sim=ROOT/f'tmp/m441_long_{variant}_gate_up_02/verilog'
        assert not (sim/'zero_exit.json').exists()
        text=(sim/'zero.log').read_text(encoding='utf-8-sig',errors='replace')
        found=re.findall(r'^M441_HEARTBEAT cycle=(\d+) output=(\d+)',text,re.M)
        assert found
        heartbeats.append(dict(variant=variant,observed_cycle=int(found[-1][0]),observed_output_words=int(found[-1][1])))
    numeric=BASE/'runs/M441-full-numeric-csim-01/RESULT.json'
    assert json.loads(numeric.read_bytes())['status']=='PASS_M441_FULL_REAL_WEIGHT_CHAIN_CSIM'
    reads={name:sha(ROOT/name) for name in ('CURRENT_STATE.md','DEPLOYMENT_OPERATION_MISTAKES_REVIEW.md','docsMILESTONES.md','deployment/mage_vl4b/BOARD_GATE_RESULT.json')}
    for name in reads:(ROOT/name).read_text(encoding='utf-8-sig')
    result=dict(status='RUNNING_M441_COMPLETE_GATEUP_ZERO_RTL_ONLY',start_sha256=sha(start),preparation_sha256=sha(prep),
                full_numeric_sha256=sha(numeric),source_state_sha256=reads,heartbeats=heartbeats,
                supervisor_pid=s['pid'],build_id='0x4D343431',board=False,RTL_completed=False,performance=False,promoted=False,
                next='One-shot controller collects original results once, checks frozen cycles before any next model; no board or shell work.')
    report='''# M441 本地离线进度

完整 gate_up、mlp_down、Q 三条真实权重链的 C 仿真已通过：417,792 个输出字、sideband、Build 和流消耗全部核对。C 仿真不能代替有限 FIFO RTL 或实板性能。

A 为原 M357（0x4D333537），B 为独立 M441（0x4D343431）。当前相同完整 gate_up 的 Zero RTL 正在运行。两份原作业均有周期/输出心跳，但尚未完成，不能据部分输出裁决加速。

一次性本地控制已启动：只收集已保存原结果；零附加延迟回退或数值/协议失败即停，不补样本；成立才推进固定 seed356 Random 和其余完整链。最大 FIFO/背压/超时及同约束路由仍是后续独立门禁，不自动整壳或上板。72h 监督预算到期仅保存未完成并保留进程。

没有启用或恢复任何定时自动化，没有新 PS 槽/CMA bank，没有板端、完整模型或新请求性能结论。M439 原 FAIL 和 M357/M437 基线保持。

最终文件将由控制在本目录生成 RESULT.json / REPORT.md；出现这些文件后只读裁决，不重新启动控制。
'''
    dest=BASE/'runs/M441-running-snapshot-01'
    atomic(dest/'REPORT.md',report.encode('utf-8'),immutable=True)
    result['report_sha256']=sha(dest/'REPORT.md');ev=dest/'RESULT.json'
    atomic(ev,encoded(result),immutable=True)
    sync('latest_m441_offline_running_snapshot',dict(status=result['status'],result=ev.relative_to(ROOT).as_posix(),sha256=sha(ev),board=False),
         f'## M441 完整长链RTL实际运行（2026-10-07）\n\nSHA {sha(ev)}；完整数值417792字PASS后，A原M357/B新M441完整gate_up Zero已启动，双方心跳有进展但尚未完成。一性有界本地控制已启动，原退出码/全输出与协议/冻结周期判据裁决后才可继续；不补样本、不自动整壳或上板。0新请求性能/晋级，M439 FAIL不改。查看 runs/M441-offline-continuation-01/PROGRESS.json；最终RESULT存在后只读。')
    print(result['status'],sha(ev),heartbeats)


if __name__=='__main__':main()
