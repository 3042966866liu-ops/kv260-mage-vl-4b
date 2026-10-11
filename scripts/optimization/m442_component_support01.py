"""Freeze the tested host controller before its first board transfer."""
import ast
import subprocess
from m441_host_io08 import atomic
from m351_workflow import ROOT, BASE, HERE, encoded, sha, sync

paths = [HERE/n for n in ('m442_component_control01.ps1','m442_component_workflow01.py','m442_component_gate01.py','m441_transfer.py')]
for p in paths:
    if p.suffix == '.py':
        ast.parse(p.read_bytes(), feature_version=(3,10))
check = subprocess.run(['C:/Users/30429/.cache/codex-runtimes/codex-primary-runtime/dependencies/native/powershell/pwsh.exe','-NoProfile','-File',str(paths[0]),'-Mode','SelfTest'],capture_output=True,check=True)
assert b'M442_COMPONENT_CONTROL_SELFTEST_PASS' in check.stdout
prep = BASE/'runs/M442-A53-parser-component-preparation-01/RESULT.json'
record = dict(status='PASS_M442_HOST_COMPONENT_SUPPORT01', board=False, checks=['Python 3.10 syntax','PowerShell syntax','Failure preserves collect','Strict transfer PASS and address restoration before component'], preparation_sha256=sha(prep), files=[dict(path=p.relative_to(ROOT).as_posix(),sha256=sha(p)) for p in paths])
out = BASE/'runs/M442-A53-parser-component-support-01/RESULT.json'
atomic(out,encoded(record),immutable=True)
sync('latest_m442_a53_component_support',dict(status=record['status'],result=out.relative_to(ROOT).as_posix(),sha256=sha(out),board=False),f'## M442实板组件控制冻结（2026-10-10）\n\nSHA {sha(out)}；失败仍回收、传输PASS/临时地址恢复前置、Python3.10与PowerShell检查通过。原冻结包/manifest不改；本阶段仅A53 CPU，不加载Overlay或请求模型。')
print(record['status'],sha(out))
