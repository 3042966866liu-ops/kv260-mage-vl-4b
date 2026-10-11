"""Preserve blocked authorization log; only choose a fresh upload precheck log."""
import json
import subprocess
from pathlib import Path
from m351_workflow import ROOT,HERE,BASE,sha,atomic,encoded,sync


def main():
    prior=BASE/'runs/M403-tail-performance-support-02/RESULT.json';value=json.loads(prior.read_bytes())
    s=(HERE/'m403_control02.ps1').read_text(encoding='utf-8')
    assert s.count('tmp/m403/sudo_upload_precheck_01.log')==1
    c=s.replace('tmp/m403/sudo_upload_precheck_01.log','tmp/m403/sudo_upload_precheck_02.log').replace('latest_m403_tail_performance_support02','latest_m403_tail_performance_support03')
    atomic(HERE/'m403_control03.ps1',c.encode('utf-8'),immutable=True)
    ps=r'C:\Users\30429\.cache\codex-runtimes\codex-primary-runtime\dependencies\native\powershell\pwsh.exe'
    p=subprocess.run([ps,'-NoProfile','-File',str(HERE/'m403_control03.ps1'),'-Mode','SelfTest'],capture_output=True,text=True,encoding='utf-8',check=True)
    assert 'M403_CONTROL_SELF_TEST_PASS' in p.stdout
    # Strict inverse confirms zero gate/transfer/collector changes.
    assert c.replace('tmp/m403/sudo_upload_precheck_02.log','tmp/m403/sudo_upload_precheck_01.log').replace('latest_m403_tail_performance_support03','latest_m403_tail_performance_support02')==s
    value.update(status='PASS_OFFLINE_TAIL_BALANCED_CONTROL_RECOVERY03',previous_support_sha256=sha(prior),blocked_shell_log_preserved=True,only_fresh_authorization_log_and_support_key_changed=True)
    value['source_sha256'].update({n:sha(HERE/n) for n in ('m403_control03.ps1','m403_control_recovery03.py','m403_interpret.py')})
    out=BASE/'runs/M403-tail-performance-support-03/RESULT.json';atomic(out,encoded(value),immutable=True);h=sha(out)
    sync('latest_m403_tail_performance_support03',dict(status=value['status'],result=out.relative_to(ROOT).as_posix(),sha256=h,manifest_sha256=value['manifest_sha256']),f'## M403 人工恢复后新授权日志控制03（2026-10-04）\n\nSHA {h}；用户已确认COM3回shell并sudo-v。原无响应日志及阻塞SHA保留，control03只换新precheck02日志和对应支持键，逆向逐字差分及SelfTest通过；包/实际编排/数值/回收/transfer路径全部保持支持02证据，轻量解读SelfTest通过。尚未上传或执行，下一步同COM3一次授权/上传，原日志不得覆盖。')
    print(value['status'],h)


if __name__=='__main__':main()
