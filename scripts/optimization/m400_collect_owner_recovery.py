"""Collect both complete or partial original-owner recovery without retrying releases."""
import json
from m351_workflow import ROOT,BASE,sha,atomic,sync
from m400_cpu_sentinel_workflow import decode


def main():
    log=ROOT/'tmp/m400/owner_recovery_run.log';text=log.read_text(encoding='utf-8-sig')
    raw,d,r=decode(text.replace('M400_RECOVER_SHA256','M400_SENTINEL_SHA256').replace('M400_RECOVER_CHUNK','M400_SENTINEL_CHUNK'))
    if r['manifest_sha256']!=sha(BASE/'candidates/M400-controlled-owner-recovery-01/PACKAGE_MANIFEST.json') or r['original_owner_pid']!=22715 or r['owner_killed']:
        raise RuntimeError('Recovery identity/scope differs')
    if '__M400_RECOVER_RUN_RC_'+str(r['gate_return_code'])+'__' not in text:raise RuntimeError('Original rc absent')
    owner=r.get('owner_result',{});closed=owner.get('owned_close',{})
    released=closed.get('release_wrapper_states')==['released']*7
    if released and ([x['allocation_order'] for x in closed['release_records']]!=list(range(6,-1,-1)) or not all(closed[k] for k in ('scope_closed','tail_closed','original_engine_closed','patch_registry_cleared'))):
        raise RuntimeError('Original closure accounting differs')
    out=BASE/'runs/M400-controlled-owner-recovery-board-01/BOARD_RESULT.json'
    atomic(out,raw,immutable=True);atomic(out.parent/'UART.log',log.read_bytes(),immutable=True)
    sync('latest_m400_controlled_owner_recovery_board',dict(status=r['status'],result=out.relative_to(ROOT).as_posix(),sha256=d,
         original_seven_DMA_released=released,stable_overlay_restored=owner.get('stable_overlay_restored',False),
         original_owner_exited=r.get('original_owner_exited',False)),
         f'## M400 原owner协作回收实际结果（2026-10-04）\n\nSHA `{d}`，原rc{r["gate_return_code"]}；七原DMA已释放={released}，scope/tail/原engine/patch关闭，真实七包装器released且逆序6..0，各后端一次。稳定恢复={owner.get("stable_overlay_restored",False)}，原owner退出={r.get("original_owner_exited",False)}；恢复入口把STABLE全局当作函数局部发生KeyError，原进程在保留循环，未kill/新DMA/模型重跑。只修恢复/退出阶段，绝不重复已完成释放或原单层硬件；原失败与旧性能保持。')
    print(json.dumps(dict(raw_sha256=d,status=r['status'],owner_result=owner,final_owner_state=r['final_owner_state']),ensure_ascii=False,indent=2))


if __name__=='__main__':main()
