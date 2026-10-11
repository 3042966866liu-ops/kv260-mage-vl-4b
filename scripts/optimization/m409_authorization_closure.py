"""Preserve login-only refusal and freeze narrow guarded resume controller."""
import json,subprocess
from m351_workflow import ROOT,BASE,HERE,atomic,encoded,sha,sync

def main():
    log=ROOT/'tmp/m40901/sudo_upload.log';text=log.read_text(encoding='utf-8-sig')
    assert 'kria login:' in text and 'sudo -n true' not in text
    old=(HERE/'m409_control.ps1').read_text(encoding='utf-8')
    needle="$board=Get-Content -LiteralPath (Join-Path $workspace 'deployment/mage_vl4b/BOARD_GATE_RESULT.json') -Raw -Encoding UTF8 | ConvertFrom-Json\n"
    assert old.count(needle)==1
    guard="if ((Get-FileHash -LiteralPath $PSCommandPath -Algorithm SHA256).Hash.ToLowerInvariant() -ne $board.latest_m409_authorization_block.resume_control_sha256) { throw 'Resume source drift' }\n"
    modified=old.replace(needle,needle+guard).replace('tmp/m40901/sudo_upload.log','tmp/m40901/sudo_upload_02.log')
    assert modified.replace(guard,'').replace('tmp/m40901/sudo_upload_02.log','tmp/m40901/sudo_upload.log')==old
    new=HERE/'m409_control02.ps1';atomic(new,modified.encode('utf-8'),immutable=True)
    psh=r'C:\Users\30429\.cache\codex-runtimes\codex-primary-runtime\dependencies\native\powershell\pwsh.exe'
    test=subprocess.run([psh,'-NoProfile','-File',str(new),'-Mode','SelfTest'],capture_output=True)
    assert test.returncode==0 and b'M409_CONTROL_SELF_TEST_PASS' in test.stdout
    b=json.loads((ROOT/'deployment/mage_vl4b/BOARD_GATE_RESULT.json').read_bytes());support=b['latest_m409_reference_support']
    assert sha(ROOT/support['result'])==support['sha256']
    value=dict(status='BLOCKED_M409_SAME_COM3_LOGIN_REQUIRED',log=log.relative_to(ROOT).as_posix(),log_sha256=sha(log),
        shell_confirmed=False,sudo_command_sent=False,upload_started=False,reference_started=False,
        overlay_loaded=False,dma_allocations=0,fpga_transactions=0,visual_forward_calls=0,language_forward_calls=0,
        resume_control=new.relative_to(ROOT).as_posix(),resume_control_sha256=sha(new),
        narrow_reverse_difference_checked=True,resume_self_SHA_guard=True,control_failure_collect_self_test=True,
        original_package_and_source_and_support_preserved=True,original_support_sha256=support['sha256'],
        human_login_renewal_required_before_one_new_probe=True,performance_pass=False)
    out=BASE/'runs/M409-authorization-block-01/RESULT.json';atomic(out,encoded(value),immutable=True)
    sync('latest_m409_authorization_block',dict(status=value['status'],result=out.relative_to(ROOT).as_posix(),sha256=sha(out),resume_control_sha256=sha(new)),
        f'## M409 上传前登录阻塞（2026-10-06）\n\nSHA {sha(out)}；COM3回到kria login，shellguard未发送sudo或任何命令，0上传/参考/Overlay/DMA。原17B日志及原包/实际支持保留；已请人工登录sudo-v，无新确认不反复探测。control02仅新授权02日志和自身SHA守卫，逆向逐字差分与失败收集SelfTest通过。恢复后直接上传已准备PS精确参考，不重跑视觉捕获；没有新质量或性能结论。')
    print('M409_AUTHORIZATION_CLOSURE',sha(out),sha(new))
if __name__=='__main__':main()
