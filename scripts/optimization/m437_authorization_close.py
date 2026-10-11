"""Preserve one failed authorization receipt; prepare fresh-log resume only."""
from m351_workflow import ROOT,BASE,HERE,atomic,encoded,sha,sync
from m427_prepare import once


def main():
    log=ROOT/'tmp/m43701/board/sudo_upload_resume05.log'
    text=log.read_text(encoding='utf-8-sig')
    assert 'ubuntu@kria:~$' in text and '__M437_SUDO_RC_1__' in text and 'a password is required' in text
    folder=ROOT/'tmp/m43701/board'
    assert not (folder/'absence.log').exists() and not list(folder.glob('upload_*')) and not (folder/'run.log').exists()
    control=(HERE/'m437_control02.ps1').read_text(encoding='utf-8').replace('sudo_upload_resume05.log','sudo_upload_resume06.log')
    anchor="VerifyEvidence 'latest_m437_transfer_support'"
    addition="""VerifyEvidence 'latest_m437_authorization_precheck'
$auth=Get-Content -Raw -Encoding UTF8 -LiteralPath (Join-Path $workspace $board.latest_m437_authorization_precheck.result) | ConvertFrom-Json
foreach ($p in $auth.resume_sources.PSObject.Properties) {
    if ((Get-FileHash -LiteralPath (Join-Path $PSScriptRoot $p.Name) -Algorithm SHA256).Hash.ToLowerInvariant() -ne $p.Value) { throw 'Authorization resume source changed' }
}
"""
    control=once(control,anchor,addition+anchor)
    atomic(HERE/'m437_control03.ps1',control.encode('utf-8'),immutable=True)
    r=dict(status='BLOCKED_M437_SUDO_EXPIRED_BEFORE_UPLOAD',
           log=log.relative_to(ROOT).as_posix(),log_sha256=sha(log),shell_confirmed=True,sudo_return_code=1,
           package_query_sent=False,uploaded=False,gate_started=False,overlay_loaded=False,
           requests_executed=0,temperature_measurement_enabled=False,
           manifest_sha256=sha(BASE/'candidates/M437-late11-natural-IO-performance-01/PACKAGE_MANIFEST.json'),
           original_control_sha256=sha(HERE/'m437_control02.ps1'),
           resume_sources={n:sha(HERE/n) for n in ('m437_control03.ps1','m437_authorization_close.py')})
    p=BASE/'runs/M437-authorization-precheck-01/RESULT.json';atomic(p,encoded(r),immutable=True)
    sync('latest_m437_authorization_precheck',dict(status=r['status'],result=p.relative_to(ROOT).as_posix(),sha256=sha(p),manifest_sha256=r['manifest_sha256']),
         f'## M437 同COM3上传前授权阻塞（2026-10-07）\n\nSHA {sha(p)}；COM3 shell确认后sudo rc1，需要密码。0包查询/上传/模型/Overlay/请求；原回执保留，不反复探测。29载荷640874B包、实际12次fake原stream/46负例及9组装传输负例已过。03只换新授权log并验证本记录与原源SHA，收到人工续期后直接Upload；不新增准备条件或温度测试。')
    print('M437_AUTHORIZATION_RECORD_SYNC',sha(p))


if __name__=='__main__':main()
