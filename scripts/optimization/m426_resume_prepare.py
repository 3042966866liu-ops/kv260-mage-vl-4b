"""Fresh authorization logs only; reuse passed arithmetic/recovery evidence."""
import json,subprocess
from m351_workflow import ROOT,BASE,HERE,atomic,encoded,sha,sync
def main():
    board=json.loads((ROOT/'deployment/mage_vl4b/BOARD_GATE_RESULT.json').read_bytes())
    e=board['latest_m426_range_support'];prior=json.loads((ROOT/e['result']).read_bytes())
    assert sha(ROOT/e['result'])==e['sha256'] and e['result'].endswith('M426-range-support-01/RESULT.json')
    auth=board['latest_m426_authorization_precheck'];assert sha(ROOT/auth['result'])==auth['sha256']
    sources={}
    for old,new in (('m426_control.ps1','m426_control02.ps1'),('m426_workflow.py','m426_workflow02.py')):
        text=(HERE/old).read_text(encoding='utf-8')
        modified=text.replace('m42601','m42602').replace('m426_workflow.py','m426_workflow02.py')
        assert modified.replace('m42602','m42601').replace('m426_workflow02.py','m426_workflow.py')==text
        atomic(HERE/new,modified.encode('utf-8'),immutable=True);sources[new]=sha(HERE/new)
    cp=subprocess.run(['C:/Users/30429/.cache/codex-runtimes/codex-primary-runtime/dependencies/native/powershell/pwsh.exe','-NoProfile','-File',str(HERE/'m426_control02.ps1'),'-Mode','SelfTest'],capture_output=True)
    atomic(ROOT/'tmp/m42602/control.stdout.bin',cp.stdout,immutable=True);atomic(ROOT/'tmp/m42602/control.stderr.bin',cp.stderr,immutable=True)
    assert cp.returncode==0 and b'M426_CONTROL_SELF_TEST_PASS' in cp.stdout
    value=dict(prior,status='READY_M426_FRESH_AUTHORIZATION_LOGS',original_support_sha256=e['sha256'],authorization_stop_sha256=auth['sha256'],
        control_and_workflow_only_log_directory_changed=True,passed_numeric_and_recovery_tests_not_repeated=True,
        source_sha256=dict(prior['source_sha256'],**sources),package_uploaded=False,software_screen_started=False)
    out=BASE/'runs/M426-authorization-recovery-01/RESULT.json';atomic(out,encoded(value),immutable=True)
    sync('latest_m426_range_support',dict(status=value['status'],result=out.relative_to(ROOT).as_posix(),sha256=sha(out),manifest_sha256=value['manifest_sha256'],board_run=False,performance_pass=False),f'## M426 人工续期待恢复入口（2026-10-06）\n\nSHA {sha(out)}；01授权失败及原日志保留，02控制/工作流仅日志目录变更，反向文本差分验证与控制自测通过；同包/算法/34回收负例复用不重跑。尚未再次访问COM3、未上传或执行。人工续期后直接用m426_control02 Upload→Run，禁止覆写01证据。')
    print('M426_FRESH_CONTROL_READY',sha(out))
if __name__=='__main__':main()
