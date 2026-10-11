"""Preserve an authorization-only stop and prepare new receipt paths."""
import subprocess
from m351_workflow import ROOT, BASE, HERE, atomic, encoded, sha, sync
from m430_workflow import PKG


def main():
    folder = ROOT / 'tmp/m43002'
    log = folder / 'sudo_upload.log'
    text = log.read_text(encoding='utf-8-sig')
    assert '__M430_SUDO_RC_1__' in text and 'a password is required' in text and 'ubuntu@kria:~$' in text
    assert not (folder / 'absence.log').exists() and not list(folder.glob('upload_*'))
    workflow = (HERE / 'm430_workflow.py').read_text(encoding='utf-8')
    old = "folder=ROOT/'tmp/m43002';rows=[]"
    new = "folder=ROOT/'tmp/m43003';rows=[]"
    assert workflow.count(old) == 1
    revised = workflow.replace(old, new)
    assert revised.replace(new, old) == workflow
    atomic(HERE / 'm430_workflow03.py', revised.encode('utf-8'), immutable=True)
    control = (HERE / 'm430_control.ps1').read_text(encoding='utf-8')
    revised_control = control.replace('tmp/m43002/', 'tmp/m43003/').replace("'m430_workflow.py'", "'m430_workflow03.py'")
    anchor = "if ($Mode -eq 'Upload') {"
    guard = """VerifyEvidence 'latest_m430_authorization_precheck'
$auth=Get-Content -LiteralPath (Join-Path $workspace $board.latest_m430_authorization_precheck.result) -Raw -Encoding UTF8 | ConvertFrom-Json
foreach ($p in $auth.resume_source_sha256.PSObject.Properties) {
    if ((Get-FileHash -LiteralPath (Join-Path $PSScriptRoot $p.Name) -Algorithm SHA256).Hash.ToLowerInvariant() -ne $p.Value) { throw 'Resume source changed' }
}
"""
    assert revised_control.count(anchor) == 1
    revised_control = revised_control.replace(anchor, guard + anchor)
    atomic(HERE / 'm430_control03.ps1', revised_control.encode('utf-8'), immutable=True)
    pwsh = 'C:/Users/30429/.cache/codex-runtimes/codex-primary-runtime/dependencies/native/powershell/pwsh.exe'
    cp = subprocess.run([pwsh, '-NoProfile', '-File', str(HERE / 'm430_control03.ps1'), '-Mode', 'SelfTest'], capture_output=True)
    atomic(ROOT / 'tmp/m43003/support_control_stdout.bin', cp.stdout, immutable=True)
    atomic(ROOT / 'tmp/m43003/support_control_stderr.bin', cp.stderr, immutable=True)
    assert cp.returncode == 0 and b'M430_CONTROL_SELF_TEST_PASS' in cp.stdout
    record = dict(
        status='M430_WAIT_SAME_COM3_SUDO_RENEWAL_NO_UPLOAD', manifest_sha256=sha(PKG / 'PACKAGE_MANIFEST.json'),
        shell_confirmed=True, sudo_return_code=1, authorization_log='tmp/m43002/sudo_upload.log',
        authorization_log_sha256=sha(log), board_packet_absence_not_queried=True,
        upload_started=False, hardware_gate_started=False, model_forward_calls=0, overlay_loads=0,
        temperature_measurement_enabled=False, performance_samples_started=0,
        resume_source_sha256={name: sha(HERE / name) for name in ('m430_control03.ps1', 'm430_workflow03.py')},
        resume_equivalence='Workflow03 changes only transfer receipt folder; check/decode/score/output remain identical. Control03 changes only receipt/workflow paths and adds exact resume source guard.',
        original_sources_preserved={name: sha(HERE / name) for name in ('m430_control.ps1', 'm430_workflow.py', 'm430_support.py')},
        next_step='After fresh manual same-COM3 shell and sudo confirmation, invoke m430_control03.ps1 Upload once, then Run. Existing saved run/result permits Collect only.')
    out = BASE / 'runs/M430-authorization-precheck-01/RESULT.json'
    atomic(out, encoded(record), immutable=True)
    digest = sha(out)
    sync('latest_m430_authorization_precheck', dict(status=record['status'], result=out.relative_to(ROOT).as_posix(), sha256=digest, manifest_sha256=record['manifest_sha256']),
         f'## M430 完整视觉性能上传前授权阻塞（2026-10-06）\n\nSHA {digest}。COM3 shell已确认，sudo rc1需要密码；未查询packet、上传、运行或加载Overlay，0计时样本。后11层M429数值PASS保持，M430固定4预热+8正式视觉协议和轻量计时包已准备；尚无新视觉性能结论。原日志/控制/工作流/支持源码保持同SHA；03恢复版仅改新回执路径并增加同SHA保护，SelfTest通过。等待人工同COM3续期后直接Upload/Run，不重复阻塞探测，不测温。')
    print('M430_AUTHORIZATION_PRECHECK_SYNC', digest)


if __name__ == '__main__':
    main()
