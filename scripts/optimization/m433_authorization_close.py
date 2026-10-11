"""Preserve actual COM3 sudo refusal; prepare only a fresh authorization receipt."""
import json
from m351_workflow import ROOT, BASE, HERE, atomic, encoded, sha, sync
from m427_prepare import once


def main():
    folder = ROOT / 'tmp/m43301/board'
    log = folder / 'sudo_upload.log'
    text = log.read_text(encoding='utf-8-sig')
    if '__M433_SUDO_RC_1__' not in text or 'ubuntu@kria:~$' not in text:
        raise RuntimeError('Actual authorization refusal not confirmed')
    if any((folder / name).exists() for name in ('absence.log', 'assembly.log', 'run.log')) or list(folder.glob('upload_*')):
        raise RuntimeError('Unexpected post-authorization operation exists')
    control = (HERE / 'm433_control02.ps1').read_text(encoding='utf-8')
    control = control.replace("'tmp/m43301/board/sudo_upload.log'", "'tmp/m43301/board/sudo_upload_resume01.log'")
    control = once(control, "VerifyEvidence 'latest_m433_actual_transfer_support'", "VerifyEvidence 'latest_m433_authorization_precheck'\n$recovery=Get-Content -Raw -Encoding UTF8 -LiteralPath (Join-Path $workspace $board.latest_m433_authorization_precheck.result) | ConvertFrom-Json\nforeach ($p in $recovery.resume_sources.PSObject.Properties) { if ((Get-FileHash -LiteralPath (Join-Path $PSScriptRoot $p.Name) -Algorithm SHA256).Hash.ToLowerInvariant() -ne $p.Value) { throw 'Resumed authorization control changed' } }\nVerifyEvidence 'latest_m433_actual_transfer_support'")
    atomic(HERE / 'm433_control03.ps1', control.encode('utf-8'), immutable=True)
    record = dict(status='M433_WAIT_SAME_COM3_SUDO_NO_UPLOAD', shell_confirmed=True, sudo_return_code=1,
        authorization_log=log.relative_to(ROOT).as_posix(), authorization_log_sha256=sha(log),
        no_package_presence_probe=True, no_upload=True, no_performance_run=True, no_overlay_load=True,
        manifest_sha256=sha(BASE / 'candidates/M433-late11-complete-request-warm-01/PACKAGE_MANIFEST.json'),
        previous_control_sha256=sha(HERE / 'm433_control02.ps1'),
        resume_sources={'m433_control03.ps1': sha(HERE / 'm433_control03.ps1')},
        only_resume_change='Fresh sudo upload receipt and immutable recovery-source guard; original upload/Run/result receipts and packet preserved.',
        M432_numerical_PASS_unchanged=True, temperature_measurement_enabled=False)
    out = BASE / 'runs/M433-authorization-precheck-01/RESULT.json'
    atomic(out, encoded(record), immutable=True)
    sync('latest_m433_authorization_precheck', dict(status=record['status'], result=out.relative_to(ROOT).as_posix(), sha256=sha(out), manifest_sha256=record['manifest_sha256']),
        f'## M433 完整请求性能上传前授权阻塞（2026-10-07）\n\nSHA {sha(out)}；COM3 shell已确认，sudo rc1需要密码，0包查询/上传/性能样本/Overlay。M432两次完整请求数值PASS已严格回收闭合；M433固定4＋8协议、递归闭包、轻量实际provider/stream/保存函数/export/host/control/组装/传输配套齐备，39回收/来源负例及9传输负例通过。三次离线fixture拒绝与原脚本日志保留；03恢复控制只换新sudo回执并核源码SHA，原包不改。等待同COM3续期后直接Upload/Run，不重复阻塞探测，不测温。')
    print('M433_AUTHORIZATION_SYNC', sha(out))


if __name__ == '__main__':
    main()
