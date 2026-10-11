"""Save one failed same-terminal authorization check; no serial actions."""
from m351_workflow import ROOT,BASE,sha,atomic,encoded,sync
def main():
    p=ROOT/'tmp/m376/sudo_precheck_01.log';raw=p.read_bytes();t=raw.decode('utf-8-sig')
    if '__M376_CHECK_SUDO_RC_1__' not in t or 'password is required' not in t:raise RuntimeError('Original sudo failure missing')
    out=BASE/'runs/M376-authorization-precheck-01';atomic(out/'UART.log',raw,immutable=True)
    result=dict(status='BLOCKED_SAME_COM3_SUDO_EXPIRED',target_build_id='0x4D333537',shell_confirmed=True,
        sudo_return_code=1,uart_sha256=sha(out/'UART.log'),uploaded=False,overlay_loaded=False,board_gate_started=False,
        next_step='Wait for human same COM3 sudo-v renewal; one fresh check before transfer; no repeated probes')
    atomic(out/'RESULT.json',encoded(result),immutable=True);digest=sha(out/'RESULT.json')
    sync('latest_m376_authorization_precheck',dict(status=result['status'],result=(out/'RESULT.json').relative_to(ROOT).as_posix(),sha256=digest,board_gate_started=False),
        f'## M376 双解析worker组件同COM3授权阻塞（2026-10-03）\n\nshell已确认，sudo rc1需密码；未上传/Overlay/CPU门禁/FPGA。原日志保存，证据SHA {digest}。已请人工PuTTY sudo-v续期后关闭，无恢复确认不重复检查；继续隔离数值门禁准备，原源码/服务/64MiB/回滚不变。')
    print(result['status'],digest)
if __name__=='__main__':main()
