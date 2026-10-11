"""Archive a successful same-COM3 authorization receipt without board calls."""
from m351_workflow import ROOT,BASE,sha,atomic,encoded,sync

def main():
    log=ROOT/'tmp/m375/sudo_precheck_01.log'
    raw=log.read_bytes()
    if '__M375_PRECHECK_SUDO_RC_0__' not in raw.decode('utf-8-sig'):
        raise RuntimeError('Same-terminal sudo PASS absent')
    out=BASE/'runs/M375-authorization-restored-01'
    atomic(out/'UART.log',raw,immutable=True)
    result=dict(status='PASS_SAME_COM3_SUDO_RENEWED',build_id='0x4D333537',
                uart_sha256=sha(out/'UART.log'),gate_started=False,
                original_failure_preserved=True,next_step='Finish upload SHA/triad, then one gate')
    atomic(out/'RESULT.json',encoded(result),immutable=True);digest=sha(out/'RESULT.json')
    sync('latest_m375_authorization_restored',dict(status=result['status'],sha256=digest,result=(out/'RESULT.json').relative_to(ROOT).as_posix()),
         f'## M375 人工续期后同COM3授权恢复\n\n用户已续期，同终端sudo rc0，旧rc1日志/结果不覆盖。新证据SHA {digest}。正在上传冻结包，门禁尚未开始；全部板端SHA/bash-n与传输三同步后才执行一次原视频窄观察。')
    print(result['status'],digest)

if __name__=='__main__':main()
