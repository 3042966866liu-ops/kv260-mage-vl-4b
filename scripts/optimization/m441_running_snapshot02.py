"""Read running job ownership/logs and record scope; starts no tool."""
import json
import re
from m351_workflow import ROOT,BASE,HERE,atomic,encoded,sha,sync
from m441_continue_offline import opened,exit_code,kernel

def main():
    dest=BASE/'runs/M441-running-snapshot-02';assert not dest.exists()
    recovery={}
    for name in ('CURRENT_STATE.md','docsMILESTONES.md','DEPLOYMENT_OPERATION_MISTAKES_REVIEW.md','deployment/mage_vl4b/BOARD_GATE_RESULT.json'):
        p=ROOT/name;t=p.read_text(encoding='utf-8-sig');recovery[name]=dict(sha256=sha(p),characters=len(t))
    full=BASE/'runs/M441-offline-continuation-01'
    follow=BASE/'runs/M441-protocol-continuation-01'
    assert not (full/'RESULT.json').exists() and not (follow/'RESULT.json').exists()
    owners=[];progress=[]
    prep=json.loads((full/'PREPARATION.json').read_bytes())
    for row in prep['owners']:
        handle,born=opened(row['pid'],row['creation_FILETIME']);assert handle is not None
        try:code=exit_code(handle)
        finally:kernel.CloseHandle(handle)
        sim=ROOT/f"tmp/m441_long_{row['variant']}_gate_up_02/verilog"
        log=sim/'zero.log';t=log.read_text(encoding='utf-8-sig',errors='replace')
        beats=re.findall(r'M441_HEARTBEAT cycle=(\d+) output=(\d+)',t)
        assert code==259 and beats and not (sim/'zero_exit.json').exists()
        owners.append(dict(variant=row['variant'],pid=row['pid'],creation_FILETIME=born,process_exit_code=code,
                           last_cycle=int(beats[-1][0]),last_output_words=int(beats[-1][1]),goal_output_words=311296,
                           note='Partial progress only; no cycle or speed verdict'))
    for folder in (full,follow):
        start=json.loads((folder/'START.json').read_bytes());handle,born=opened(start['pid']);assert handle is not None
        try:code=exit_code(handle)
        finally:kernel.CloseHandle(handle)
        assert code==259
        progress.append(dict(path=folder.relative_to(ROOT).as_posix(),pid=start['pid'],creation_FILETIME=born,
                             process_exit_code=code,last_event=json.loads((folder/'PROGRESS.json').read_bytes())[-1]))
    result=dict(status='RUNNING_M441_COMPLETE_RTL_WITH_FINITE_FOLLOWUP',build_id='0x4D343431',owners=owners,supervisors=progress,
        recovery_read=recovery,full_CSim_sha256='a2b19009642bc956a3a18cd01a09fb3d65bb187ea1672ce2a4bd853bb1256c46',
        protocol_control_preparation_sha256='c687c2f8d3d9a617ab3b465c812ee28f9a48d5983654cbc739ff63b77d54e53a',
        core_preparation_sha256='ff8b9ad03a8744a7b9d24618977f7c9f6aa63714a492f370e065de4655f80e8c',
        protocol_continuation_preparation_sha256=sha(follow/'PREPARATION.json'),
        board=False,full_shell=False,RTL_complete=False,performance=False,promoted=False,processes_killed=False,
        next='Existing full-chain RTL continues. A complete passing comparison unlocks core routed timing, then maximum protocol and expected timeout. Each saved result synchronizes three records. Failure or budget expiry stops without restart or process kill.')
    ev=dest/'RESULT.json';atomic(ev,encoded(result),immutable=True)
    report='# M441 持续验证当前状态\n\n完整长链 RTL 原版/候选仍在运行，两个有限控制器均存活。当前计数仅证明推进，不代表最终周期或实板提速。\n\n'
    for x in owners:report+=f'- {x["variant"]}: {x["last_cycle"]} 模拟周期，输出 {x["last_output_words"]}/{x["goal_output_words"]} 字。\n'
    report+='\n本次完成后续控制准入、31项协议收集故障检查复用、同约束核级实现准备。完整长链通过后自动逐级收集核时序、最大FIFO/背压、预期超时，失败停止，原日志不重跑。\n\n没有访问COM3、切换板端、构建整壳或宣称新性能收益。当前无需用户输入密码。\n'
    atomic(dest/'REPORT.md',report.encode('utf-8'),immutable=True)
    sync('latest_m441_running_snapshot02',dict(status=result['status'],result=ev.relative_to(ROOT).as_posix(),sha256=sha(ev),board=False),
         f'## M441 持续离线验证已接续（2026-10-07）\n\nSHA {sha(ev)}；A/B原长链控制器与两个有限监督进程实际存活，当前输出未完成，不是RTL或实板性能PASS。31项协议收集故障检查复用，后续准入与同约束核时序准备完成。完整RTL成功才自动核OOC→最大FIFO/背压→timeout，每级原证据三记录同步，失败/到期不kill或重跑。0COM3/整壳/新部署，M439 FAIL及M437基线保持。')
    print(result['status'],sha(ev));print(json.dumps(owners,ensure_ascii=False))

if __name__=='__main__':main()
