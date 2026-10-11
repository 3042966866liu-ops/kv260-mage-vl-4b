"""Collect saved restore-only result and close recovery evidence before any new gate."""
import json
from m351_workflow import ROOT,BASE,sha,atomic,sync
from m400_cpu_sentinel_workflow import decode


def main():
    log=ROOT/'tmp/m400/owner_restore_run.log';text=log.read_text(encoding='utf-8-sig')
    raw,d,r=decode(text.replace('M400_RECOVER_SHA256','M400_SENTINEL_SHA256').replace('M400_RECOVER_CHUNK','M400_SENTINEL_CHUNK'))
    if r['manifest_sha256']!=sha(BASE/'candidates/M400-controlled-owner-restore-02/PACKAGE_MANIFEST.json') or r['original_owner_pid']!=22715 or r['owner_killed']:
        raise RuntimeError('Restore identity/scope differs')
    if '__M400_RECOVER_RUN_RC_'+str(r['gate_return_code'])+'__' not in text:raise RuntimeError('Original rc absent')
    owner=r.get('owner_result',{})
    if r['gate_return_code']==0:
        if r['status']!='PASS_CONTROLLED_OWNER_EXIT_AND_STABLE_RESTORE' or owner['gate_return_code'] or not owner['no_release_retried']:
            raise RuntimeError('Incomplete restore PASS')
        for obj,keys in [(r,('original_owner_exited','execution_lock_released','original_failure_unchanged')),
                         (owner,('stable_overlay_restored','original_failure_unchanged'))]:
            if not all(obj[k] for k in keys):raise RuntimeError('Incomplete exit/stable restore')
        if owner['stable_bit_sha256']!='1cbf7bbb86cfe64c2349418d5a15890d735bea3fa4c999060c8a9da9ac3206ac' or owner['stable_restore_transaction_submitted']:
            raise RuntimeError('Stable identity/lifecycle differs')
        closed=owner['closed_state_rechecked']
        if not all(closed[k] for k in ('scope_closed','engine_closed','seven_original_wrappers_released','patch_registry_cleared','no_release_retried')) or [x['allocation_order'] for x in closed['release_records']]!=list(range(6,-1,-1)):
            raise RuntimeError('Original closure ledger differs')
    elif not r.get('traceback'):raise RuntimeError('Unknown restoration failure')
    out=BASE/'runs/M400-controlled-owner-restore-board-02/BOARD_RESULT.json'
    atomic(out,raw,immutable=True);atomic(out.parent/'UART.log',log.read_bytes(),immutable=True)
    sync('latest_m400_controlled_owner_restore_board',dict(status=r['status'],result=out.relative_to(ROOT).as_posix(),sha256=d,
         original_owner_exited=r.get('original_owner_exited',False),stable_overlay_restored=owner.get('stable_overlay_restored',False),
         original_seven_DMA_released=True,layer_numerical_pass=False),
         f'## M400 原owner稳定恢复/退出结果（2026-10-04）\n\nSHA `{d}`，原rc{r["gate_return_code"]}，{r["status"]}；原七DMA已由原owner释放，02不再次close/free，关闭状态/逆序ledger重新核对；稳定恢复={owner.get("stable_overlay_restored",False)}，原owner退出={r.get("original_owner_exited",False)}，执行锁已释放={r.get("execution_lock_released",False)}。原失败raw保持，不kill/模型重跑/新DMA；稳定fresh Overlay无事务，不当已完成DMA idle。只闭合回收，不是单层数值PASS。下一步新不可变单层包，源码/原SHA/确定性同解释器AST检查在Overlay和DMA之前，停同级；文本/视频/新性能未解锁。')
    report=f'''# M400 原owner受控回收

原始单层 gate 仍为 FAIL_UNSAFE_RETAINED，raw SHA de7f6e0e144fe03529a414f3983e2e6e515bc8a7d7185400daf5e026bcd549e9。没有模型Linear，只有一次合法最小事务。

目标 Python 3.10 已复现三处元组赋值括号差异，同解释器 AST 相同。新确定性源检查保留原完整 SHA，前置入口在硬件 gate 导入之前拒绝异常。

原 PID22715 的实际 scope 无映射/绑定/解析任务，七缓冲身份一致。独立 CPU 哨兵先验证了原主线程关闭及幂等释放。GDB 默认共享库符号加载超过预算；关闭 auto-solib-add 后只读附加及内部检查通过。

原主线程协作入口调用原 scope.close、engine.close；原七包装器逐块检查安全，逆序6..0释放。恢复入口首轮把模块全局 STABLE 当成函数局部导致失败，已保留该原结果。02 合并原 frame 的 globals/locals，只检查已关闭状态并恢复 Overlay、退出，没有重复释放。

最终状态：{r['status']}。稳定恢复：{owner.get('stable_overlay_restored',False)}；原进程退出：{r.get('original_owner_exited',False)}；执行锁释放：{r.get('execution_lock_released',False)}。结果 SHA {d}。

稳定 Overlay 是新加载、没有提交事务，初始 DMA 状态不作为已完成事务空闲证明。稳定 rollback、boot/DTB/CMA、生产准入和旧 40.81% 性能结论保持。

下一步仅新版本同级单层验证。原单层数值尚未通过，不能扩大到文本或视频。
'''
    atomic(out.parent/'REPORT.md',report.encode('utf-8'),immutable=True)
    print(json.dumps(dict(status=r['status'],sha256=d,owner=owner,final_owner_state=r['final_owner_state']),ensure_ascii=False))


if __name__=='__main__':main()
