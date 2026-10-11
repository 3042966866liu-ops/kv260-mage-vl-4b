"""Preserve failed sudo check; new authorization log only after human renewal."""
import json,subprocess
from m351_workflow import ROOT,BASE,HERE,atomic,encoded,sha,sync
def main():
    log=ROOT/'tmp/m41401/sudo_upload.log';text=log.read_text(encoding='utf-8-sig')
    assert 'ubuntu@kria:~$' in text and '__M414_SUDO_RC_1__' in text and 'password is required' in text
    original=(HERE/'m414_control.ps1').read_text(encoding='utf-8')
    derived=original.replace('tmp/m41401/sudo_upload.log','tmp/m41401/sudo_upload02.log')
    anchor="foreach ($key in @('latest_m409_reference_board'"
    assert derived.count(anchor)==1
    guard="""VerifyEvidence 'latest_m414_visual_authorization_precheck'
$auth=$board.latest_m414_visual_authorization_precheck
if ((Get-FileHash -LiteralPath $PSCommandPath -Algorithm SHA256).Hash.ToLowerInvariant() -ne $auth.controller02_sha256) { throw 'Recovery control identity drift' }
"""
    derived=derived.replace(anchor,guard+anchor)
    assert derived.replace(guard,'').replace('tmp/m41401/sudo_upload02.log','tmp/m41401/sudo_upload.log')==original
    atomic(HERE/'m414_control02.ps1',derived.encode('utf-8'),immutable=True)
    tested=subprocess.run([r'C:\Users\30429\.cache\codex-runtimes\codex-primary-runtime\dependencies\native\powershell\pwsh.exe','-NoProfile','-File',str(HERE/'m414_control02.ps1'),'-Mode','SelfTest'],capture_output=True)
    assert tested.returncode==0 and b'M414_CONTROL_SELF_TEST_PASS' in tested.stdout
    board=json.loads((ROOT/'deployment/mage_vl4b/BOARD_GATE_RESULT.json').read_bytes())
    value=dict(status='BLOCKED_M414_UPLOAD_SUDO_RENEWAL_REQUIRED',manifest_sha256=board['latest_m414_layer12_visual_preparation']['manifest_sha256'],
               actual_shell_confirmed=True,sudo_return_code=1,original_UART_log=log.relative_to(ROOT).as_posix(),original_UART_log_sha256=sha(log),
               files_uploaded=0,overlay_loads=0,DMA_allocations=0,visual_forward_calls=0,PL_transactions=0,
               hardware_quality_or_performance=False,repeated_password_attempts=0,
               controller02_sha256=sha(HERE/'m414_control02.ps1'),controller01_preserved_sha256=sha(HERE/'m414_control.ps1'),
               inverse_exact_control_diff=True,controller_failure_collection_selftest=True,
               next_concrete_step='After human sudo-v renewal only: control02 Upload then Run exactly once; existing result/run log means Collect only.')
    out=BASE/'runs/M414-authorization-precheck-01/RESULT.json';atomic(out,encoded(value),immutable=True)
    sync('latest_m414_visual_authorization_precheck',dict(status=value['status'],result=out.relative_to(ROOT).as_posix(),sha256=sha(out),controller02_sha256=value['controller02_sha256']),
         f'## M414 上传前同终端sudo阻塞（2026-10-06）\n\nSHA {sha(out)}；COM3真实shell已确认，sudo原rc1，需要人工sudo-v续期。0上传/Overlay/DMA/视觉/PL，未重复尝试密码；原日志和控制01保留。02只新授权日志并绑定自身SHA，逆向逐字差分及故意失败收集SelfTest通过；新人工续期后直接Upload→Run一次完整视觉质量，不新增准备或扩层。')
    print('M414_AUTHORIZATION_BLOCK_SYNC',sha(out),value['controller02_sha256'])
if __name__=='__main__':main()
