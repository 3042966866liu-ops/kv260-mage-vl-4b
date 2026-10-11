"""Close one explicit sudo refusal; preserve original receipt and prepare fresh resume."""
import subprocess
from m351_workflow import ROOT,BASE,HERE,atomic,encoded,sha,sync


def main():
    log=ROOT/'tmp/m43501/board/sudo_upload_resume01.log'
    text=log.read_text(encoding='utf-8-sig')
    if '__M435_SUDO_RC_1__' not in text or 'ubuntu@kria:' not in text:
        raise RuntimeError('Exact shell/sudo refusal absent')
    if (ROOT/'tmp/m43501/board/absence.log').exists() or (ROOT/'tmp/m43501/board/run.log').exists():
        raise RuntimeError('Upload/gate boundary no longer unstarted')
    original=(HERE/'m435_control.ps1').read_text(encoding='utf-8')
    if original.count('sudo_upload_resume01.log')!=2:raise RuntimeError('Fresh authorization receipt anchor differs')
    resumed=original.replace('sudo_upload_resume01.log','sudo_upload_resume02.log')
    anchor="foreach ($row in $manifest.files) {"
    if resumed.count(anchor)!=1:raise RuntimeError('Control resume verification anchor differs')
    resumed=resumed.replace(anchor,"""VerifyEvidence 'latest_m435_authorization_precheck'
$auth=Get-Content -Raw -Encoding UTF8 -LiteralPath (Join-Path $workspace $board.latest_m435_authorization_precheck.result) | ConvertFrom-Json
foreach ($p in $auth.resume_sources.PSObject.Properties) {
    if ((Get-FileHash -LiteralPath (Join-Path $PSScriptRoot $p.Name) -Algorithm SHA256).Hash.ToLowerInvariant() -ne $p.Value) { throw 'Resumed authorization source differs' }
}
"""+anchor)
    path=HERE/'m435_control02.ps1';atomic(path,resumed.encode(),immutable=True)
    ps='C:/Users/30429/.cache/codex-runtimes/codex-primary-runtime/dependencies/native/powershell/pwsh.exe'
    tested=subprocess.run([ps,'-NoProfile','-File',str(path),'-Mode','SelfTest'],capture_output=True)
    if tested.returncode or b'M435_CONTROL_SELF_TEST_PASS' not in tested.stdout:raise RuntimeError('Fresh receipt controller syntax/failure collection rejected')
    r=dict(status='BLOCKED_M435_SUDO_EXPIRED_BEFORE_UPLOAD',sudo_rc=1,shell_confirmed=True,
           receipt=log.relative_to(ROOT).as_posix(),receipt_sha256=sha(log),uploaded=False,board_gate_started=False,
           overlay_loaded=False,model_forward_calls=0,resume_sources={n:sha(HERE/n) for n in ('m435_control.ps1','m435_control02.ps1','m435_workflow.py')},
           new_receipt='tmp/m43501/board/sudo_upload_resume02.log',original_receipt_preserved=True,
           required='Human same-COM3 sudo -v, return to shell, close PuTTY; check once with fresh receipt')
    out=BASE/'runs/M435-authorization-precheck-01/RESULT.json';atomic(out,encoded(r),immutable=True)
    sync('latest_m435_authorization_precheck',dict(status=r['status'],result=out.relative_to(ROOT).as_posix(),sha256=sha(out)),f'## M435 上传前同COM3授权阻塞（2026-10-07）\n\nSHA {sha(out)}；shell已确认，sudo rc1，0上传/诊断/Overlay/模型。原回执SHA {sha(log)}保留，已明确要求人工sudo-v，未反复检查。02控制只改新授权回执并强制本记录/原新控制SHA，通过语法及故意失败收集自测；恢复后直接manifest-first900B上传及固定BB窄观察，不性能重跑、不测温。')
    print('M435_AUTHORIZATION_SYNC',sha(out))


if __name__=='__main__':main()
