"""Freeze actual prepared board controls and record offline checks only."""
import ast,json,subprocess,sys
from m351_workflow import ROOT,BASE,HERE,atomic,encoded,sha,sync
OUT=ROOT/'tmp/m439_board_support_01'
proof=BASE/'runs/M439-board-support-preparation-01/RESULT.json'
r=json.loads(proof.read_bytes())
for row in r['files']:assert sha(ROOT/row['path'])==row['sha256']
names=['m439_control.ps1','m439_transfer.py','m439_transfer_collection.py','m439_export_result.py','m439_gate_runner.sh','m439_board_probe.py','m439_completion_observer.py']
for name in names:
    p=HERE/name
    assert not p.exists(), 'Control already frozen; inspect only'
    atomic(p,(OUT/name).read_bytes(),immutable=True)
    if p.suffix=='.py':ast.parse(p.read_text(encoding='utf-8'),feature_version=(3,10))
checked=[]
commands=[['C:/Users/30429/.cache/codex-runtimes/codex-primary-runtime/dependencies/native/powershell/pwsh.exe','-NoProfile','-File',str(HERE/'m439_control.ps1'),'-Mode','SelfTest'],[sys.executable,'-B',str(HERE/'test_m439_board_support.py')]]
for argv in commands:
    completed=subprocess.run(argv,cwd=ROOT,capture_output=True,timeout=30)
    checked.append(dict(argv=argv,return_code=completed.returncode,stdout=completed.stdout.decode('utf-8',errors='replace'),stderr=completed.stderr.decode('utf-8',errors='replace')))
    assert completed.returncode==0,checked[-1]
controls=names+['m439_comparison.py','m439_board_collection.py','test_m439_board_support.py','m439_prepare_board_support.py','m439_freeze_board_controls.py']
value=dict(status='PASS_M439_BOARD_SUPPORT_AND_FAILURE_COLLECTION_OFFLINE',build_id='0x4D343339',preparation_sha256=sha(proof),checks=checked,tests_run=16,actual_prepared_probe_sha256=sha(OUT/'m439_board_probe.py'),files=[dict(path=(HERE/n).relative_to(ROOT).as_posix(),sha256=sha(HERE/n)) for n in controls],fake_devices_only=True,board=False,full_shell_pass_required=True,rejected_offline_checks=['First run sandbox TEMP fixture permission; no device execution.','Harness still expected old generic minimal-zero label; updated to actual precise candidate-build-id, no probe change.'],source_harness_sha256=sha(HERE/'test_m357_board_probe.py'))
p=BASE/'runs/M439-board-support-checks-01/RESULT.json';atomic(p,encoded(value),immutable=True)
sync('latest_m439_board_support_checks',dict(status=value['status'],result=p.relative_to(ROOT).as_posix(),sha256=sha(p),build_id=value['build_id'],board=False),'## M439 板端支持与回收离线检查（2026-10-07）\n\nSHA '+sha(p)+'；16项fake设备/实际新probe与收集检查、控制故意失败后仍收集PASS，活动DMA保留owner/锁/全部缓冲、不超时kill。错误A核/样本遗漏/错释放/活动DMA/计时伪造/时钟不同/静默恢复64MiB门槛均拒绝；新控制冻结。首次离线TEMP权限及旧通用label断言保留，0真实设备；整壳PASS后才打包上板。')
print(value['status'],sha(p))
