"""Host-log preservation only; frozen board runner and package unchanged."""
import json,subprocess
from m351_workflow import ROOT,BASE,HERE,atomic,encoded,sha,sync
original=HERE/'m439_control.ps1';s=original.read_text(encoding='utf-8')
for a,b in [('tmp/m439_board/sudo_bootstrap.log','tmp/m439_board/sudo_bootstrap_renewed02.log'),('${taskLabel}_sudo.log','${taskLabel}_${Mode}_sudo.log'),('${taskLabel}_root_syntax.log','${taskLabel}_${Mode}_root_syntax.log')]:
    # Existing source uses lowercase variable label, case matters only to this guard.
    a=a.replace('taskLabel','taskLabel')
    if a.startswith('${taskLabel}'):
        a=a.replace('${taskLabel}','${taskLabel}')
    # PowerShell source interpolation spelling is ${taskLabel}? Actual string
    # inspected separately; compare case-insensitively, preserve original text.
    import re
    matches=list(re.finditer(re.escape(a),s,re.I));assert len(matches)==1,(a,len(matches))
    m=matches[0];s=s[:m.start()]+b+s[m.end():]
target=HERE/'m439_control02.ps1';atomic(target,s.encode('utf-8'),immutable=True)
r=subprocess.run(['C:/Users/30429/.cache/codex-runtimes/codex-primary-runtime/dependencies/native/powershell/pwsh.exe','-NoProfile','-File',str(target),'-Mode','SelfTest'],capture_output=True,timeout=15)
assert r.returncode==0,(r.stdout,r.stderr)
value=dict(status='PASS_M439_HOST_LOG_PRESERVATION_REPAIR_ONLY',original_controller_sha256=sha(original),controller02_sha256=sha(target),package_manifest_sha256=sha(BASE/'candidates/M439-record-load-01/PACKAGE_MANIFEST.json'),selftest_rc=r.returncode,changed_fields=['Renewed bootstrap sudo host log name','Gate Run versus Collect sudo and bash-n host log names'],board_payload_changed=False,board_runner_changed=False,gate_order_changed=False,prior_authorization_result_preserved=True,prior_sudo_log_overwritten=True,limitation='Renewed Bootstrap reused legacy sudo_bootstrap.log and replaced first refused sudo bytes. Earlier immutable authorization RESULT retains original rc1/SHA, but original log bytes no longer exist at its path. Do not claim original log still hash-valid. New host log names separate collection from execution.',board_gate_executed=False)
p=BASE/'runs/M439-host-log-repair-02/RESULT.json';atomic(p,encoded(value),immutable=True)
sync('latest_m439_host_log_repair',dict(status=value['status'],result=p.relative_to(ROOT).as_posix(),sha256=sha(p),build_id='0x4D343339',board=False),'## M439 主机授权日志保存修正（2026-10-07）\n\nSHA '+sha(p)+'；续期Bootstrap继承旧固定sudo日志名覆盖首次rc1日志，原失败RESULT及其SHA保留，但原日志字节不再在旧路径，不宣称仍可回核。02只分离续期及Run/Collect本地sudo/syntax日志名，控制SelfTest PASS，板端包/runner/门禁顺序完全不变；后续使用02，0新硬件事务。')
print(value['status'],sha(p))
