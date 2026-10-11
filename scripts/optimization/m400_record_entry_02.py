"""Save tested pre-entry and one authorization refusal; no board access."""
from m351_workflow import ROOT,HERE,BASE,sha,atomic,encoded,sync


def main():
    log=ROOT/'tmp/m400/sentinel_sudo_Upload.log'
    if '__M400_SENTINEL_SUDO_RC_1__' not in log.read_text(encoding='utf-8-sig'):
        raise RuntimeError('Expected terminal sudo refusal absent')
    out=BASE/'runs/M400-recovery-authorization-precheck-02/RESULT.json'
    value=dict(status='BLOCKED_SAME_TERMINAL_SUDO_EXPIRED',receipt_sha256=sha(log),
               original_owner_recovered=False,seven_DMA_retained=True,stable_overlay_restored=False,
               sentinel_uploaded=False,sentinel_executed=False,new_overlay_loads=0)
    atomic(out,encoded(value),immutable=True);atomic(out.parent/'UART.log',log.read_bytes(),immutable=True);d=sha(out)
    sync('latest_m400_recovery_authorization',dict(status=value['status'],result=out.relative_to(ROOT).as_posix(),sha256=d),
         f'## M400 受控回收授权前置（2026-10-04）\n\nSHA `{d}`；COM3 shell确认，sudo原rc1。CPU哨兵尚未上传/执行，原PID22715挂起、七DMA保留、稳定Overlay未恢复。只等待人工sudo-v，不反复检查或猜密码；原失败与旧性能结论保持。')
    out=BASE/'runs/M400-layer-pre-entry-preparation-02/RESULT.json'
    value=dict(status='PASS_OFFLINE_SOURCE_PRECHECK_BEFORE_GATE_IMPORT',
               source_sha256={n:sha(HERE/n) for n in ('m400_layer_entry_02.py','test_m400_layer_entry_02.py','m400_tail_source_02.py')},
               checks=['actual entry runs complete manifest bytes/SHA and deterministic source guard before importing gate',
                       'bad manifest refuses before gate import','unavailable source refuses before gate import',
                       'frozen payload drift refuses before gate import','extra file refuses before gate import',
                       'default off without explicit flag','accepted guard precedes explicit fake gate import/main'],
               import_target_is_explicit_fake=True,actual_overlay_or_DMA_test=False,
               board_package_assembled=False,original_owner_recovered=False,
               actual_target_source_guard_evidence_sha256='eff06d0d82518a68d36e799de9b317ffa3aacb8a06bf952b84069ae5c5d07314')
    atomic(out,encoded(value),immutable=True);d=sha(out)
    sync('latest_m400_layer_pre_entry_preparation',dict(status=value['status'],result=out.relative_to(ROOT).as_posix(),sha256=d),
         f'## M400 资源申请前源码入口检查（2026-10-04）\n\nSHA `{d}`；实际stdlib入口先完整manifest/文件SHA及确定性源码/同解释器AST检查，再导入硬件gate。manifest/源缺失/冻结载荷/额外文件/default-off拒绝和接受顺序检查通过；gate导入明确替身，未执行Overlay/DMA。原SHA保留、原冻结包不改；新单层包尚未组装，原owner未回收，不解锁文本/视频。')
    print('M400_AUTHORIZATION_AND_PRE_ENTRY_RECEIPTS_SYNCHRONIZED',d)


if __name__=='__main__':main()
