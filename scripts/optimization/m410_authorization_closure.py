"""Preserve single failed authorization; next confirmation uses a new log only."""
import subprocess
from m351_workflow import ROOT,BASE,HERE,atomic,encoded,sha,sync
def main():
    log=ROOT/'tmp/m41001/sudo_upload.log';t=log.read_text(encoding='utf-8-sig')
    assert '__M410_SUDO_RC_1__' in t and 'password is required' in t and 'ubuntu@kria:' in t
    old=(HERE/'m410_control.ps1').read_text(encoding='utf-8')
    new=old.replace('tmp/m41001/sudo_upload.log','tmp/m41001/sudo_upload_02.log')
    anchor="$board=Get-Content -LiteralPath (Join-Path $workspace 'deployment/mage_vl4b/BOARD_GATE_RESULT.json') -Raw -Encoding UTF8 | ConvertFrom-Json\n"
    guard="if ((Get-FileHash -LiteralPath $PSCommandPath -Algorithm SHA256).Hash.ToLowerInvariant() -ne $board.latest_m410_authorization_block.resume_control_sha256) { throw 'Resume source drift' }\n"
    assert old.count(anchor)==1 and old.count('tmp/m41001/sudo_upload.log')==2
    new=new.replace(anchor,anchor+guard)
    assert new.replace(anchor+guard,anchor).replace('tmp/m41001/sudo_upload_02.log','tmp/m41001/sudo_upload.log')==old
    path=HERE/'m410_control02.ps1';atomic(path,new.encode('utf-8'),immutable=True)
    psh=r'C:\Users\30429\.cache\codex-runtimes\codex-primary-runtime\dependencies\native\powershell\pwsh.exe'
    test=subprocess.run([psh,'-NoProfile','-File',str(path),'-Mode','SelfTest'],capture_output=True)
    assert test.returncode==0 and b'M410_CONTROL_SELF_TEST_PASS' in test.stdout
    value=dict(status='BLOCKED_M410_SAME_COM3_SUDO_EXPIRED',shell_confirmed=True,sudo_rc=1,authorization_log=log.relative_to(ROOT).as_posix(),authorization_log_sha256=sha(log),
        upload_started=False,overlay_loaded=False,fpga_transactions=0,original_control_preserved=True,resume_control_sha256=sha(path),reverse_exact_difference=True,SelfTest=True,next_step='After new user renewal confirmation: control02 Upload, then Descriptor once; synchronize before Chain.')
    out=BASE/'runs/M410-authorization-block-01/RESULT.json';atomic(out,encoded(value),immutable=True)
    sync('latest_m410_authorization_block',dict(status=value['status'],result=out.relative_to(ROOT).as_posix(),sha256=sha(out),resume_control_sha256=sha(path)),
        f'## M410 视觉最小门禁同终端授权阻塞（2026-10-06）\n\nSHA {sha(out)}；COM3 shell已确认，sudo原rc1需要人工续期；未上传/Overlay/DMA/PL。原日志/包/支持/控制保持，control02仅独立02授权日志和自身SHA守卫，逆向逐字差分/失败收集SelfTest通过。48项回收负例和原硬件证据保持；新人工续期后直接上传，单descriptor闭合后才双descriptor链，无新确认不反复探测。')
    print('M410_AUTHORIZATION_SYNC',sha(out),sha(path))
if __name__=='__main__':main()
