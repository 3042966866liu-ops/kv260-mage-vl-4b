"""Close an authorization-only stop; prepare fresh immutable receipt paths."""
import json,subprocess
from m351_workflow import ROOT,BASE,HERE,atomic,encoded,sha,sync
from m429_workflow import PKG

def main():
    log=ROOT/'tmp/m42902/sudo_upload.log';text=log.read_text(encoding='utf-8-sig')
    assert '__M429_SUDO_RC_1__' in text and 'a password is required' in text and 'ubuntu@kria:~$' in text
    assert not (ROOT/'tmp/m42902/absence.log').exists() and not list((ROOT/'tmp/m42902').glob('upload_*'))
    # Preserve original control, workflow, support and authorization log bytes.
    workflow=(HERE/'m429_workflow.py').read_text(encoding='utf-8')
    revised=workflow.replace("folder=ROOT/'tmp/m42902';receipts=[]","folder=ROOT/'tmp/m42903';receipts=[]")
    assert revised!=workflow and revised.replace("folder=ROOT/'tmp/m42903';receipts=[]","folder=ROOT/'tmp/m42902';receipts=[]")==workflow
    atomic(HERE/'m429_workflow03.py',revised.encode('utf-8'),immutable=True)
    control=(HERE/'m429_control.ps1').read_text(encoding='utf-8')
    new=control.replace('tmp/m42902/','tmp/m42903/').replace("'m429_workflow.py'","'m429_workflow03.py'")
    anchor="if ($Mode -eq 'Upload') {"
    guard="""VerifyEvidence 'latest_m429_authorization_precheck'
$auth=Get-Content -LiteralPath (Join-Path $workspace $board.latest_m429_authorization_precheck.result) -Raw -Encoding UTF8 | ConvertFrom-Json
foreach ($p in $auth.resume_source_sha256.PSObject.Properties) {
    if ((Get-FileHash -LiteralPath (Join-Path $PSScriptRoot $p.Name) -Algorithm SHA256).Hash.ToLowerInvariant() -ne $p.Value) { throw 'Resume source changed' }
}
"""
    assert new.count(anchor)==1;new=new.replace(anchor,guard+anchor)
    atomic(HERE/'m429_control03.ps1',new.encode('utf-8'),immutable=True)
    pwsh='C:/Users/30429/.cache/codex-runtimes/codex-primary-runtime/dependencies/native/powershell/pwsh.exe'
    cp=subprocess.run([pwsh,'-NoProfile','-File',str(HERE/'m429_control03.ps1'),'-Mode','SelfTest'],capture_output=True)
    atomic(ROOT/'tmp/m42903/support_control_stdout.bin',cp.stdout,immutable=True);atomic(ROOT/'tmp/m42903/support_control_stderr.bin',cp.stderr,immutable=True)
    assert cp.returncode==0 and b'M429_CONTROL_SELF_TEST_PASS' in cp.stdout
    record=dict(status='M429_WAIT_SAME_COM3_SUDO_RENEWAL_NO_UPLOAD',manifest_sha256=sha(PKG/'PACKAGE_MANIFEST.json'),shell_confirmed=True,sudo_return_code=1,
        authorization_log='tmp/m42902/sudo_upload.log',authorization_log_sha256=sha(log),board_packet_absence_not_queried=True,
        upload_started=False,hardware_gate_started=False,model_forward_calls=0,overlay_loads=0,temperature_measurement_enabled=False,
        resume_source_sha256={name:sha(HERE/name) for name in ('m429_control03.ps1','m429_workflow03.py')},
        resume_equivalence='Workflow03 changes only transfer receipt folder; gate/check/decode math and output path remain identical. Control03 changes only new receipt/workflow paths plus exact resume source guard.',
        original_support_sources_unchanged=True,next_step='After fresh manual shell+sudo confirmation, invoke m429_control03.ps1 Upload once, then Run. Existing saved run/result may only Collect; do not repeat model or PL gates.')
    out=BASE/'runs/M429-authorization-precheck-01/RESULT.json';atomic(out,encoded(record),immutable=True)
    sync('latest_m429_authorization_precheck',dict(status=record['status'],result=out.relative_to(ROOT).as_posix(),sha256=sha(out),manifest_sha256=record['manifest_sha256']),
        f'## M429 COM3上传前授权阻塞（2026-10-06）\n\nSHA {sha(out)}；shell已确认，sudo rc1需要密码，未查询packet/上传/运行/加载Overlay；原日志同SHA保留。后11层完整视觉数值02包和离线门禁已齐，03恢复控制只改新回执路径并核同SHA，SelfTest通过。需要人工同COM3续期后直接Upload/Run，不继续同阻塞探测，不测温。')
    print('M429_AUTHORIZATION_PRECHECK_SYNC',sha(out))

if __name__=='__main__':main()
