"""Record the single failed same-terminal authorization, no serial calls."""
from m351_workflow import ROOT,BASE,atomic,encoded,sha,sync
def main():
    log=ROOT/'tmp/m42601/sudo_upload.log';text=log.read_text(encoding='utf-8-sig')
    assert 'ubuntu@kria:' in text and '__M426_SUDO_RC_1__' in text and 'a password is required' in text
    assert not (ROOT/'tmp/m42601/absence.log').exists() and not (ROOT/'tmp/m42601/run.log').exists()
    r=dict(status='BLOCKED_M426_SAME_COM3_SUDO_EXPIRED',shell_confirmed=True,sudo_rc=1,
        log=log.relative_to(ROOT).as_posix(),log_sha256=sha(log),package_uploaded=False,software_screen_started=False,
        overlay_loaded=False,dma_allocations=0,fpga_transactions=0,feature_screen_pass=False,task_screen_pass=False,performance_pass=False,
        next_step='Operator sudo-v at COM3 then shell and close PuTTY; use fresh versioned authorization logs, no repeated password attempts. Packet and prior component evidence unchanged.')
    out=BASE/'runs/M426-authorization-precheck-01/RESULT.json';atomic(out,encoded(r),immutable=True)
    sync('latest_m426_authorization_precheck',dict(status=r['status'],result=out.relative_to(ROOT).as_posix(),sha256=sha(out),board_run=False,performance_pass=False),f'## M426 COM3授权前置停止（2026-10-06）\n\nSHA {sha(out)}；shell已确认，sudo rc1需要人工密码；软件包未上传、视觉筛查未执行，无Overlay/DMA/事务/测温。完整准备及组件证据保留；不重复探测密码，人工续期后用新日志恢复上传。')
    print('M426_AUTH_STOP_SYNC',sha(out))
if __name__=='__main__':main()
