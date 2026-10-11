"""Freeze actual support and exercise existing safety/collection harness locally."""
import ast,json,subprocess,sys
from m351_workflow import ROOT,BASE,HERE,atomic,encoded,sha,sync
OUT=ROOT/'tmp/m441_board_support_07'
prep=BASE/'runs/M441-board-support-preparation-07/RESULT.json';p=json.loads(prep.read_bytes())
for row in p['files']:assert sha(ROOT/row['path'])==row['sha256']
names=['m441_control07.ps1','m441_transfer.py','m441_transfer_collection.py','m441_export_result.py',
       'm441_gate_runner.sh','m441_board_probe.py','m441_completion_observer.py','m441_comparison.py','m441_board_collection.py']
for name in names:
    assert not (HERE/name).exists(),'Already frozen: inspect only'
    atomic(HERE/name,(OUT/name).read_bytes(),immutable=True)
source=(HERE/'test_m439_board_support.py').read_text(encoding='utf-8-sig')
source=source.replace('m439','m441').replace('M439','M441').replace('0x4d343339','0x4d343431').replace('0x4D343339','0x4D343431')
source=source.replace('tmp/m441_board_support_01','tmp/m441_board_support_07')
source=source.replace("elif mode=='Descriptor':load('B');group('B','descriptor:w2','w2')", "elif mode=='Descriptor':\n        load('B')\n        for name in ('w2','w4'):group('B','descriptor:'+name,name)")
source=source.replace("elif mode=='Chain':load('B');group('B','chain:q','q_full');group('B','chain:w4','w4_chain')", "elif mode=='Chain':\n        load('B')\n        for name in ('q_full','gate_up_full','mlp_down_full'):group('B','chain:'+name,name)")
source=source.replace("['w2','w4','q_full']","['gate_up_full','mlp_down_full']")
source=source.replace("['comparison']['cases']['w2']","['comparison']['cases']['gate_up_full']")
ast.parse(source,feature_version=(3,10));atomic(HERE/'test_m441_board_support07.py',source.encode(),immutable=True)
commands=[['C:/Users/30429/.cache/codex-runtimes/codex-primary-runtime/dependencies/native/powershell/pwsh.exe','-NoLogo','-NoProfile','-File',str(HERE/'m441_control07.ps1'),'-Mode','SelfTest'],
          [sys.executable,'-B','-X','utf8',str(HERE/'test_m441_board_support07.py')]]
checks=[]
for cmd in commands:
    r=subprocess.run(cmd,cwd=ROOT,capture_output=True,timeout=60)
    checks.append(dict(command=cmd,rc=r.returncode,stdout=r.stdout.decode('utf-8',errors='replace'),stderr=r.stderr.decode('utf-8',errors='replace')))
ok=all(r['rc']==0 for r in checks)
r=dict(status='PASS_M441_BOARD_SUPPORT_AND_FAILURE_COLLECTION_OFFLINE07' if ok else 'FAIL_M441_BOARD_SUPPORT_OFFLINE07',
  build_id='0x4D343431',preparation_sha256=sha(prep),checks=checks,fake_devices_only=True,board=False,full_shell_pass_required=True,
  files=[dict(path=(HERE/n).relative_to(ROOT).as_posix(),sha256=sha(HERE/n)) for n in names+['test_m441_board_support07.py','m441_prepare_board_support07.py','m441_freeze_board_support07.py']],
  limitations='Tests use fake MMIO/buffers/memory and fabricated safe result receipts. They validate guards and collection only, not hardware or capacity.')
ev=BASE/'runs/M441-board-support-checks-07/RESULT.json';atomic(ev,encoded(r),immutable=True)
sync('latest_m441_board_support_checks07',dict(status=r['status'],result=ev.relative_to(ROOT).as_posix(),sha256=sha(ev),build_id=r['build_id'],board=False),
 f'## M441 板端支持离线检查07（2026-10-09）\n\nSHA {sha(ev)}；{r["status"]}。实际冻结probe及严格collector/control，fake设备/所有者/活动DMA/精确结果/原返回值/样本与时钟篡改检查；原M357/M9身份分别约束。记录完整stdout/stderr/退出码，0板端；失败只修此级，整壳及后续传输负例通过才打包。')
print(r['status'],sha(ev));print(json.dumps(checks,ensure_ascii=False))
raise SystemExit(0 if ok else 1)
