"""Save human recovery once; no board I/O."""
from m351_workflow import ROOT,BASE,sha,atomic,encoded,sync
log=ROOT/'tmp/m383/sudo_precheck_02.log'
assert '__M383_CHECK_SUDO_RC_0__' in log.read_text(encoding='utf-8-sig')
p=BASE/'runs/M383-authorization-recovery-01/RESULT.json'
r=dict(status='PASS_COM3_HUMAN_RECOVERY',log=log.relative_to(ROOT).as_posix(),log_sha256=sha(log),sudo_return_code=0,shell_confirmed=True,previous_failed_receipt_sha256=sha(BASE/'runs/M383-authorization-precheck-01/RESULT.json'),package_uploaded=False,board_gate_started=False)
atomic(p,encoded(r),immutable=True);d=sha(p)
sync('latest_m383_authorization',dict(status=r['status'],result=p.relative_to(ROOT).as_posix(),sha256=d),f'## M383 COM3续期确认\n\n用户人工续期后新02日志确认shell及同终端sudo rc0，恢复SHA {d}；失败01原样保留。未上传/Overlay。下一步已冻结包manifest-first/900B核对。')
print(d)
