"""Record the one auth refusal and prepare fresh logs; no second COM3 check."""
import json,subprocess
from m351_workflow import ROOT,BASE,HERE,atomic,encoded,sha,sync
def main():
    b=json.loads((ROOT/'deployment/mage_vl4b/BOARD_GATE_RESULT.json').read_bytes());e=b['latest_m420_combination_support'];assert sha(ROOT/e['result'])==e['sha256'];support=json.loads((ROOT/e['result']).read_bytes())
    for name,digest in support['source_sha256'].items():assert sha(HERE/name)==digest
    log=ROOT/'tmp/m42001/sudo_upload.log';assert '__M420_SUDO_RC_1__' in log.read_text(encoding='utf-8-sig')
    blocker=dict(status='BLOCKED_M420_SUDO_BEFORE_UPLOAD',log_sha256=sha(log),original_sudo_return_code=1,shell_confirmed=True,upload_started=False,visual_forward_calls=0,overlay_loads=0,DMA_allocations=0,physical_PL_transactions=0,no_password_attempt=True,no_repeated_probe=True,manifest_sha256=support['manifest_sha256'])
    out=BASE/'runs/M420-authorization-precheck-01/RESULT.json';atomic(out,encoded(blocker),immutable=True)
    sync('latest_m420_authorization_precheck',dict(status=blocker['status'],result=out.relative_to(ROOT).as_posix(),sha256=sha(out),manifest_sha256=blocker['manifest_sha256']),f'## M420 上传前sudo阻塞（2026-10-06）\n\nSHA {sha(out)}；COM3实际shell已确认，sudo原rc1；0上传/Overlay/DMA/视觉/PL，不重复探测或密码尝试。第13层完整MLP通过结论保持，12＋13组合包和44配套拒绝检查已完成；待人工续期后直接上传同SHA包，原授权日志保留。')
    old=(HERE/'m420_control.ps1').read_text(encoding='utf-8')
    new=old.replace('tmp/m42001','tmp/m42002').replace('m420_workflow02.py','m420_workflow03.py').replace('latest_m420_combination_support','latest_m420_combination_authorization_recovery')
    assert new.replace('tmp/m42002','tmp/m42001').replace('m420_workflow03.py','m420_workflow02.py').replace('latest_m420_combination_authorization_recovery','latest_m420_combination_support')==old
    atomic(HERE/'m420_control02.ps1',new.encode('utf-8'),immutable=True)
    oldw=(HERE/'m420_workflow02.py').read_text(encoding='utf-8');neww=oldw.replace('tmp/m42001','tmp/m42002');assert neww.replace('tmp/m42002','tmp/m42001')==oldw;atomic(HERE/'m420_workflow03.py',neww.encode('utf-8'),immutable=True)
    psh=r'C:\Users\30429\.cache\codex-runtimes\codex-primary-runtime\dependencies\native\powershell\pwsh.exe'
    check=subprocess.run([psh,'-NoProfile','-File',str(HERE/'m420_control02.ps1'),'-Mode','SelfTest'],capture_output=True);assert check.returncode==0 and b'M420_CONTROL_SELF_TEST_PASS' in check.stdout
    v=dict(status='PASS_M420_FRESH_AUTHORIZATION_LOG_CONTROLLER_ONLY',manifest_sha256=support['manifest_sha256'],original_blocker_sha256=sha(out),unchanged_full_support_sha256=e['sha256'],packet_unchanged=True,math_collection_unmodified=True,only_auth_log_and_host_guard_changed=True,control_failure_collect_SelfTest=True,board_run=False,await_user_sudo=True,
        source_sha256={n:sha(HERE/n) for n in ('m420_authorization_recovery.py','m420_control02.ps1','m420_workflow03.py')})
    out=BASE/'runs/M420-authorization-recovery-01/RESULT.json';atomic(out,encoded(v),immutable=True)
    sync('latest_m420_combination_authorization_recovery',dict(status=v['status'],result=out.relative_to(ROOT).as_posix(),sha256=sha(out),manifest_sha256=v['manifest_sha256']),f'## M420 授权日志受控恢复准备（2026-10-06）\n\nSHA {sha(out)}；原rc1和日志不覆盖。02控制器仅新授权/传输日志、对应host guard和收集器默认日志目录；逆向逐字差分及故意失败仍收集SelfTest通过。原完整44配套检查、包/数学/三视觉协议同SHA，不重跑；等待人工sudo-v回复后直接Upload/Run。0新COM3探测/硬件/视觉。')
    print('M420_AUTHORIZATION_RECOVERY_READY',sha(out))
if __name__=='__main__':main()
