"""Preserve the actual authorization failure and bind the recovery controller."""
import json, subprocess
from m351_workflow import ROOT, BASE, HERE, atomic, encoded, sha, sync

def main():
    log=ROOT/'tmp/m41601/sudo_upload.log'
    text=log.read_text(encoding='utf-8-sig')
    assert 'ubuntu@kria:~$' in text and '__M416_SUDO_RC_1__' in text and 'password is required' in text
    original=(HERE/'m416_control.ps1').read_text(encoding='utf-8')
    anchor="foreach ($key in @('latest_m416_bounded_expansion_plan'"
    assert original.count(anchor)==1
    guard="""$auth=$board.latest_m416_local_mlp_authorization_precheck
if ((Get-FileHash -LiteralPath (Join-Path $workspace $auth.result) -Algorithm SHA256).Hash.ToLowerInvariant() -ne $auth.sha256) { throw 'Authorization evidence drift' }
if ((Get-FileHash -LiteralPath $PSCommandPath -Algorithm SHA256).Hash.ToLowerInvariant() -ne $auth.controller02_sha256) { throw 'Recovery control identity drift' }
foreach ($n in @('CURRENT_STATE.md','docsMILESTONES.md')) {
    if (-not (Get-Content -LiteralPath (Join-Path $workspace $n) -Raw -Encoding UTF8).Contains($auth.sha256)) { throw 'Authorization evidence not synchronized' }
}
"""
    derived=original.replace('tmp/m41601/sudo_upload.log','tmp/m41601/sudo_upload02.log').replace(anchor,guard+anchor)
    assert derived.replace(guard,'').replace('tmp/m41601/sudo_upload02.log','tmp/m41601/sudo_upload.log')==original
    control=HERE/'m416_control02.ps1'
    atomic(control,derived.encode('utf-8'),immutable=True)
    test=subprocess.run([r'C:\Users\30429\.cache\codex-runtimes\codex-primary-runtime\dependencies\native\powershell\pwsh.exe','-NoProfile','-File',str(control),'-Mode','SelfTest'],capture_output=True)
    assert test.returncode==0 and b'M416_CONTROL_SELF_TEST_PASS' in test.stdout
    board=json.loads((ROOT/'deployment/mage_vl4b/BOARD_GATE_RESULT.json').read_bytes())
    value=dict(status='BLOCKED_M416_UPLOAD_SUDO_RENEWAL_REQUIRED',manifest_sha256=board['latest_m416_local_mlp_support04']['manifest_sha256'],
               actual_shell_confirmed=True,sudo_return_code=1,original_UART_log=log.relative_to(ROOT).as_posix(),original_UART_log_sha256=sha(log),
               files_uploaded=0,overlay_loads=0,DMA_allocations=0,visual_forward_calls=0,PL_transactions=0,
               repeated_password_attempts=0,controller02_sha256=sha(control),controller01_preserved_sha256=sha(HERE/'m416_control.ps1'),
               inverse_exact_control_diff=True,controller_failure_collection_selftest=True,
               next_concrete_step='Only after human renewal: control02 Upload then Run once, existing result/run log means Collect only.')
    out=BASE/'runs/M416-authorization-precheck-01/RESULT.json'
    atomic(out,encoded(value),immutable=True)
    sync('latest_m416_local_mlp_authorization_precheck',dict(status=value['status'],result=out.relative_to(ROOT).as_posix(),sha256=sha(out),controller02_sha256=sha(control)),
         f'## M416 上传前同终端sudo阻塞（2026-10-06）\n\nSHA {sha(out)}；COM3实际shell已确认，sudo原rc1，需要人工sudo-v续期。0上传/Overlay/DMA/视觉/PL，未重复尝试密码。原控制器和授权日志保留；02只使用新授权日志及绑定自身SHA，逆向逐字差分和故意失败收集SelfTest通过。收到人工续期后直接上传第13层PS捕获包并执行一次，已有结果只回收。')
    print('M416_AUTHORIZATION_BLOCK_SYNC',sha(out),sha(control))

if __name__=='__main__':main()
