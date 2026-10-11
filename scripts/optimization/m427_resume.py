"""Record one sudo refusal, prepare fresh logs, reuse unchanged passed tests."""
import json,subprocess
from m351_workflow import ROOT,BASE,HERE,atomic,encoded,sha,sync

def main():
    board=json.loads((ROOT/'deployment/mage_vl4b/BOARD_GATE_RESULT.json').read_bytes())
    e=board['latest_m427_half_support'];prior=json.loads((ROOT/e['result']).read_bytes())
    assert sha(ROOT/e['result'])==e['sha256']
    log=ROOT/'tmp/m42701/sudo_upload.log';text=log.read_text(encoding='utf-8-sig')
    assert '__M427_SUDO_RC_1__' in text and 'a password is required' in text and 'ubuntu@kria:' in text
    auth=dict(status='BLOCKED_M427_SAME_COM3_SUDO_EXPIRED',authorization_exit_code=1,shell_confirmed=True,
        log_sha256=sha(log),manifest_sha256=prior['manifest_sha256'],package_uploaded=False,software_gate_started=False,
        no_Overlay_DMA_or_model=True,do_not_repeat_same_blocked_probe=True)
    p=BASE/'runs/M427-authorization-precheck-01/RESULT.json';atomic(p,encoded(auth),immutable=True)
    sync('latest_m427_authorization_precheck',dict(status=auth['status'],result=p.relative_to(ROOT).as_posix(),sha256=sha(p),manifest_sha256=prior['manifest_sha256'],board_run=False),
        f'## M427 上板授权前置暂停（2026-10-06）\n\nSHA {sha(p)}；COM3 shell确认，sudo-n原rc1需要密码，0上传/模型/Overlay/DMA。42负例与组件已过，未重复探测。人工续期后使用独立02日志恢复，包与实验不变。')
    fresh={}
    for old,new in (('m427_control.ps1','m427_control02.ps1'),('m427_workflow.py','m427_workflow02.py')):
        original=(HERE/old).read_text(encoding='utf-8')
        text=original.replace('tmp/m42701','tmp/m42702').replace('m427_workflow.py','m427_workflow02.py')
        assert text.replace('tmp/m42702','tmp/m42701').replace('m427_workflow02.py','m427_workflow.py')==original
        atomic(HERE/new,text.encode('utf-8'),immutable=True);fresh[new]=sha(HERE/new)
    cp=subprocess.run(['C:/Users/30429/.cache/codex-runtimes/codex-primary-runtime/dependencies/native/powershell/pwsh.exe','-NoProfile','-File',str(HERE/'m427_control02.ps1'),'-Mode','SelfTest'],capture_output=True)
    atomic(ROOT/'tmp/m42702/control.stdout.bin',cp.stdout,immutable=True);atomic(ROOT/'tmp/m42702/control.stderr.bin',cp.stderr,immutable=True)
    assert cp.returncode==0 and b'M427_CONTROL_SELF_TEST_PASS' in cp.stdout
    r=dict(prior,status='READY_M427_FRESH_AUTHORIZATION_LOGS',original_support_sha256=e['sha256'],authorization_stop_sha256=sha(p),
        passed_component_and_42_recovery_checks_not_repeated=True,control_only_fresh_log_paths=True,
        source_sha256=dict(prior['source_sha256'],**fresh),package_uploaded=False,software_gate_started=False)
    out=BASE/'runs/M427-authorization-recovery-01/RESULT.json';atomic(out,encoded(r),immutable=True)
    sync('latest_m427_half_support',dict(status=r['status'],result=out.relative_to(ROOT).as_posix(),sha256=sha(out),manifest_sha256=r['manifest_sha256'],board_run=False),
        f'## M427 待人工续期的独立恢复控制（2026-10-06）\n\nSHA {sha(out)}；01拒绝日志保留，02控制/回收仅换日志目录，反向文本相等及控制自测通过。原组件/42回收负例不重复，包同SHA。收到人工恢复后直接m427_control02 Upload→Run，未再次检查COM3。')
    print('M427_AUTHORIZATION_STOP_AND_FRESH_CONTROL_SYNC',sha(p),sha(out))
if __name__=='__main__':main()
