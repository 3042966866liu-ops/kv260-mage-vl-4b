"""Preserve one failed same-terminal authorization check; no board access."""
from m351_workflow import ROOT,BASE,sha,atomic,encoded,sync
def main():
    p=ROOT/'tmp/m401/sudo_upload_precheck_01.log';raw=p.read_bytes();text=raw.decode('utf-8-sig')
    assert '__M401_UPLOAD_SUDO_RC_1__' in text and 'a password is required' in text
    out=BASE/'runs/M401-authorization-precheck-01';atomic(out/'UART.log',raw,immutable=True)
    value=dict(status='BLOCKED_SAME_TERMINAL_SUDO',UART_sha256=sha(out/'UART.log'),shell_confirmed=True,sudo_rc=1,uploaded=False,gate_started=False,overlay_loaded=False,model_forward_calls=0,fpga_transactions=0,
               next_step='Await explicit operator same-COM3 sudo-v renewal; do not repeat the blocked check without response.')
    atomic(out/'RESULT.json',encoded(value),immutable=True);h=sha(out/'RESULT.json')
    sync('latest_m401_authorization_precheck',dict(status=value['status'],result=(out/'RESULT.json').relative_to(ROOT).as_posix(),sha256=h),
         f'## M401 COM3上传前授权阻塞（2026-10-04）\n\nSHA `{h}`；shell已确认，sudo rc1需要密码，上传0/Overlay0/模型0/FPGA0。固定文本包和离线支持已完成，等待用户同COM3 sudo-v续期及关闭PuTTY；不重复同阻塞或尝试密码。M400已完成单层PASS与稳定恢复，未新增板端资源。')
    print(value|{'sha256':h})
if __name__=='__main__':main()
