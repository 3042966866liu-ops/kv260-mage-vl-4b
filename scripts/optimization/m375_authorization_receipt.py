"""Preserve this one failed authorization check; no serial or hardware calls."""
from m351_workflow import ROOT,BASE,sha,atomic,encoded,sync

def main():
    source=ROOT/'tmp/m375/sudo_precheck_01.log'
    raw=source.read_bytes();text=raw.decode('utf-8-sig')
    if '__M375_PRECHECK_SUDO_RC_1__' not in text or 'password is required' not in text:
        raise RuntimeError('Expected original sudo failure absent')
    out=BASE/'runs/M375-authorization-precheck-01'
    atomic(out/'UART.log',raw,immutable=True)
    result=dict(status='BLOCKED_SAME_COM3_SUDO_EXPIRED',build_id='0x4D333537',
                shell_confirmed=True,sudo_return_code=1,uart_sha256=sha(out/'UART.log'),
                uploaded=False,overlay_loaded=False,board_gate_started=False,
                next_step='Wait for human same COM3 sudo-v renewal; one fresh check, upload then one Run. Do not repeat failed authorization automatically.')
    atomic(out/'RESULT.json',encoded(result),immutable=True);digest=sha(out/'RESULT.json')
    sync('latest_m375_authorization_precheck',dict(status=result['status'],result=(out/'RESULT.json').relative_to(ROOT).as_posix(),sha256=digest,board_gate_started=False),
         f'## M375 视频窄等待上板授权前置（2026-10-03）\n\nCOM3 shell已确认，同终端sudo rc1要求密码；尚未上传/Overlay/视频。原日志精确保存，证据SHA {digest}。已请求人工sudo-v后关闭PuTTY；无恢复确认不重复探测。冻结包/控制/数值参考保持，下一步续期后一次检查再Upload/Run。')
    print(result['status'],digest)

if __name__=='__main__':main()
