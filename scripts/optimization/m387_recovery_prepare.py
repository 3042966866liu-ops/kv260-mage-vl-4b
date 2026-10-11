"""Keep failed authorization immutable; prepare a new authorization log only."""
import ast,json,subprocess
from m351_workflow import ROOT,HERE,BASE,sha,atomic,encoded,sync
def main():
    log=ROOT/'tmp/m387/sudo_precheck_01.log';text=log.read_text(encoding='utf-8-sig')
    assert '__M387_CHECK_SUDO_RC_1__' in text and 'ubuntu@kria:' in text
    assert not (ROOT/'tmp/m387/component_uart.log').exists()
    p=BASE/'runs/M387-authorization-precheck-01/RESULT.json'
    r=dict(status='BLOCKED_SAME_COM3_SUDO_EXPIRED_BEFORE_UPLOAD',shell_confirmed=True,sudo_rc=1,log=log.relative_to(ROOT).as_posix(),log_sha256=sha(log),uploaded=False,overlay_loaded=False,forward=False)
    atomic(p,encoded(r),immutable=True);d=sha(p)
    sync('latest_m387_authorization_precheck',dict(status=r['status'],result=p.relative_to(ROOT).as_posix(),sha256=d),f'## M387 固定159视频上传前授权阻塞\n\nCOM3 shell确认，sudo rc1；原日志保留SHA {d}。固定文本已闭合，视频包/编排/回收支持已完成，但未上传/Overlay/forward。等待人工续期，仅使用新02日志确认一次，不重复相同探测。')
    old=HERE/'m387_control.ps1';new=HERE/'m387_control_recovered_02.ps1'
    s=old.read_text(encoding='utf-8');assert s.count('sudo_precheck_01.log')==2
    s=s.replace('sudo_precheck_01.log','sudo_precheck_02.log')
    s=s.replace('    $oldEntries=@{}',"    $secondaryEntries=@{}\n    foreach ($entry in $secondary.files) { $secondaryEntries[$entry.path]=$entry.sha256+':'+$entry.bytes }\n    $oldEntries=@{}")
    old_delta="    $delta=@($manifest.files | Where-Object { -not $oldEntries.ContainsKey($_.path) -or $oldEntries[$_.path] -ne ($_.sha256+':'+$_.bytes) } | ForEach-Object path)"
    new_delta="    $delta=@($manifest.files | Where-Object { ((-not $oldEntries.ContainsKey($_.path)) -or $oldEntries[$_.path] -ne ($_.sha256+':'+$_.bytes)) -and ((-not $secondaryEntries.ContainsKey($_.path)) -or $secondaryEntries[$_.path] -ne ($_.sha256+':'+$_.bytes)) } | ForEach-Object path)"
    assert s.count(old_delta)==1;s=s.replace(old_delta,new_delta)
    atomic(new,s.encode('utf-8'),immutable=True)
    ctl=subprocess.run(['C:/Users/30429/.cache/codex-runtimes/codex-primary-runtime/dependencies/native/powershell/pwsh.exe','-NoProfile','-File',str(new),'-Mode','SelfTest'],capture_output=True,text=True,encoding='utf-8');assert ctl.returncode==0 and 'M387_CONTROL_SELF_TEST_PASS' in ctl.stdout,ctl.stdout+ctl.stderr
    # Both transfer selector implementations must agree with exact assembly rows.
    pkg=BASE/'candidates/M387-ps-video-01';oldpkg=BASE/'candidates/M386-ps-text-01';secondpkg=BASE/'candidates/M380-gate-up-video-01'
    rows=json.loads((pkg/'PACKAGE_MANIFEST.json').read_text(encoding='utf-8'))['files'];primary={r['path']:r for r in json.loads((oldpkg/'PACKAGE_MANIFEST.json').read_text(encoding='utf-8'))['files']};second={r['path']:r for r in json.loads((secondpkg/'PACKAGE_MANIFEST.json').read_text(encoding='utf-8'))['files']}
    expected=[r['path'] for r in rows if primary.get(r['path'])!=r and second.get(r['path'])!=r]
    ps=dict(second);ps.update(primary)
    rejected=[r['path'] for r in rows if ps.get(r['path'])!=r];assert rejected!=expected
    rejected_path=BASE/'runs/M387-transfer-selector-offline-rejection-01/RESULT.json'
    value=dict(status='REJECTED_OFFLINE_TWO_SOURCE_SELECTOR',original_controller_sha256=sha(old),recovered01_sha256=sha(HERE/'m387_control_recovered.ps1'),selected=rejected,expected=expected,reason='Primary same-name row overwrote exact matching secondary row; only unnecessary transfer, no package/gate change',board_uploaded=False,board_run=False)
    atomic(rejected_path,encoded(value),immutable=True);rejsha=sha(rejected_path)
    sync('latest_m387_transfer_selector_offline_rejection',dict(status=value['status'],result=rejected_path.relative_to(ROOT).as_posix(),sha256=rejsha),f'## M387 两源传输选择离线拒绝\n\n最后核对发现主源同名不同SHA覆盖次源精确匹配条目，导致多传文件而不影响包数值；没有上传/执行。原控制及recovered01保留SHA {rejsha}，仅独立recovered02改为两源任一精确SHA/字节匹配均可复用，须实际PS选择检查通过。')
    a=s.index('    $oldManifest=Get-Content');z=s.index("    foreach ($name in (@('PACKAGE_MANIFEST.json')+$delta))",a)
    probe=ROOT/'tmp/m387/selector_actual.ps1'
    probe_text="$ErrorActionPreference='Stop'\n$workspace='"+ROOT.as_posix()+"'\n$manifest=Get-Content -LiteralPath '"+(pkg/'PACKAGE_MANIFEST.json').as_posix()+"' -Raw -Encoding UTF8 | ConvertFrom-Json\n"+s[a:z]+"ConvertTo-Json -InputObject @($delta) -Compress\n"
    atomic(probe,probe_text.encode('utf-8'),immutable=True)
    actual=subprocess.run(['C:/Users/30429/.cache/codex-runtimes/codex-primary-runtime/dependencies/native/powershell/pwsh.exe','-NoProfile','-File',str(probe)],capture_output=True,text=True,encoding='utf-8');assert actual.returncode==0,actual.stderr
    assert json.loads(actual.stdout)==expected
    evidence=dict(status='PASS_NEW_AUTHORIZATION_LOG_AND_SELECTOR_CLOSURE',original_control_sha256=sha(old),recovered_control_sha256=sha(new),only_authorization_log_and_exact_two_source_transfer_selection_changed=True,controller_failure_collects=True,two_source_transfer_selection_equals_assembly=True,actual_PowerShell_selector_executed=True,new_payload_files=expected,original_failed_log_preserved=True,offline_rejection_sha256=rejsha,board_run=False)
    p=BASE/'runs/M387-authorization-recovery-support-01/RESULT.json';atomic(p,encoded(evidence),immutable=True);d=sha(p)
    sync('latest_m387_authorization_recovery_support',dict(status=evidence['status'],result=p.relative_to(ROOT).as_posix(),sha256=d),f'## M387 授权恢复控制准备\n\n旧控制及失败01日志原样保留；独立recovered02仅改授权日志02及两源任一SHA/字节精确匹配选择，实际PowerShell选择与assembly白名单一致，故意失败仍收集/解析通过。SHA {d}；原包不改、无板端命令。收到人工续期后才检查一次。')
    print('M387_RECOVERY_SUPPORT',d,expected)
if __name__=='__main__':main()
