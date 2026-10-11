"""Preserve a COM3 prerequisite result without rechecking the terminal."""
import json
import re
import sys
from m351_workflow import ROOT,BASE,sha,atomic,encoded,sync

def main():
    source=ROOT/sys.argv[1];version=sys.argv[2]
    if not re.fullmatch('[0-9]{2}',version):raise RuntimeError('Explicit receipt version required')
    text=source.read_text(encoding='utf-8-sig');rcs=re.findall(r'__M400_UPLOAD_SUDO_RC_([01])__',text)
    if not rcs or len(set(rcs))!=1 or 'ubuntu@kria:' not in text:raise RuntimeError('Confirmed shell and one original sudo return required')
    rc=int(rcs[0]);directory=BASE/('runs/M400-authorization-precheck-'+version)
    atomic(directory/'UART.log',source.read_bytes(),immutable=True)
    value=dict(status='PASS_COM3_SUDO_PREREQUISITE' if rc==0 else 'BLOCKED_COM3_SUDO_EXPIRED',port='COM3',sudo_return_code=rc,
               original_uart_sha256=sha(directory/'UART.log'),original_uart= (directory/'UART.log').relative_to(ROOT).as_posix(),
               board_gate_started=False,password_attempted=False,source_log=source.relative_to(ROOT).as_posix())
    out=directory/'RESULT.json';atomic(out,encoded(value),immutable=True);digest=sha(out)
    step='仅同COM3受控上传/核验，仍须Run前再检查sudo。' if rc==0 else '暂停上传/上板，需人工sudo-v；不反复同阻塞，原M399 chain PASS与M400离线支持保持。'
    sync('latest_m400_authorization_precheck',dict(status=value['status'],result=out.relative_to(ROOT).as_posix(),sha256=digest),
         f'## M400 COM3授权前置记录（2026-10-04）\n\n已确认ubuntu@kria shell，sudo原rc{rc}，UART原字节独立保存，SHA `{digest}`。{step}无M400 Overlay/模型/FPGA事务，无密码尝试；原稳定回滚保持。')
    print(json.dumps(dict(status=value['status'],result_sha256=digest)))

if __name__=='__main__':main()
