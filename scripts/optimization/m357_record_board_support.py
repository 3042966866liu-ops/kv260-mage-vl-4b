"""Offline board support checks; hardware bundle remains locked."""
import ast
import argparse
import json
import re
import subprocess
import sys
from pathlib import Path
import m351_workflow as w
ROOT=Path(__file__).resolve().parents[2]
BASE=ROOT/'deployment/mage_vl4b/optimization_v1'
HERE=Path(__file__).resolve().parent
ap=argparse.ArgumentParser();ap.add_argument('--revision',choices=['02','03','04'],default='04');args=ap.parse_args()
ev=BASE/('runs/M357-board-support-preparation-'+args.revision+'/RESULT.json')
if ev.exists():raise RuntimeError('Immutable support preparation exists')
sources=['m357_board_probe.py','m357_export_result.py','m357_board_collection.py','m357_gate_runner.sh','test_m357_board_probe.py','test_m357_board_collection.py','m357_transfer.py','test_m357_transfer.py','m357_transfer_collection.py','test_m357_transfer_collection.py','m357_control.ps1']
for name in sources:
    if name.endswith('.py'):ast.parse((HERE/name).read_text(encoding='utf-8'),feature_version=(3,10))
checks=[]
for name in ['test_m357_board_probe.py','test_m357_board_collection.py','test_m357_transfer.py','test_m357_transfer_collection.py']:
    tested=subprocess.run([sys.executable,'-B',str(HERE/name)],capture_output=True,text=True,encoding='utf-8',errors='replace')
    row=dict(source=name,rc=tested.returncode,stdout=tested.stdout,stderr=tested.stderr)
    checks.append(row)
    if tested.returncode or not tested.stderr.rstrip().endswith('OK'):raise RuntimeError('Support test failed '+name+tested.stderr)
pwsh='C:/Users/30429/.cache/codex-runtimes/codex-primary-runtime/dependencies/native/powershell/pwsh.exe'
tested=subprocess.run([pwsh,'-NoProfile','-File',str(HERE/'m357_control.ps1'),'-Mode','SelfTest'],capture_output=True,text=True,encoding='utf-8',errors='replace')
checks.append(dict(source='m357_control.ps1 SelfTest',rc=tested.returncode,stdout=tested.stdout,stderr=tested.stderr))
assert tested.returncode==0 and 'M357_CONTROL_SELF_TEST_PASS' in tested.stdout
linux='/mnt/c/Users/30429/Desktop/TeLLMe_FPGA_2026/scripts/optimization/m357_gate_runner.sh'
tested=subprocess.run(['wsl.exe','-d','Ubuntu-24.04','--','/bin/bash','-n',linux],capture_output=True,text=True,encoding='utf-8',errors='replace')
checks.append(dict(source='WSL Ubuntu-24.04 bash-n runner',rc=tested.returncode,stdout=tested.stdout,stderr=tested.stderr))
assert tested.returncode==0, tested.stdout+tested.stderr
result=dict(status='PASS_OFFLINE_BOARD_SUPPORT_ONLY_HARDWARE_LOCKED',build_id='0x4D333537',checks=checks,
    files=[dict(path=(HERE/name).relative_to(ROOT).as_posix(),sha256=w.sha(HERE/name)) for name in sources],
    fixture_contract_sha256=w.sha(ROOT/'tmp/m357_board_fixture_02/BOARD_CASES.json'),
    corrected_fixture_only=True,old_preparation_retained=True,revision=args.revision,
    transfer_test_scope='Actual local socketpair complete-byte framing; fake network identity restoration. No real Ethernet/COM3/board execution.',
    fake_pynq_mmio_dma_only=True,board_executed=False,hardware_capacity_proven=False,board_numerical_pass=False,performance_pass=False,promoted=False,
    coverage='Completed numerical failure restores stable only after proven safe lifecycle; pre-submit memory rejection; active timeout retains6 buffers/Overlay/process/lock and exports original failure. Collector19 corruption/scope/lifecycle/wire rejection cases and complete PASS/retained FAIL export positives.',
    pending='Complete-shell timing and matching HWH/ABI before package or board control')
w.atomic(ev,w.encoded(result),immutable=True);digest=w.sha(ev)
# Repair only previously missing Markdown separators; all words/SHAs stay intact.
for name in ['CURRENT_STATE.md','docsMILESTONES.md']:
    path=ROOT/name;text=path.read_text(encoding='utf-8-sig');fixed=re.sub(r'([0-9a-f]{64})(?=M35[67])',r'\1\n\n',text)
    if fixed!=text:w.atomic(path,fixed.encode('utf-8'))
w.sync('M357_board_support_preparation',dict(status=result['status'],sha256=digest,evidence_path=ev.relative_to(ROOT).as_posix(),build_id='0x4D333537'),
    'M357 板测支持修订'+args.revision+'离线故障/原字节回收检查PASS，独立拒绝旧OP00短输出并绑定修正4096B fixture；本地socketpair完整字节传输、fake网络恢复、分块回收破坏负例、控制失败始终收集及bash-n通过。仅CPU假设备/本地socket，未上传/上板，无容量/数值/性能结论；整机时序/HWH通过前锁定。旧版保留。证据 '+digest)
print(json.dumps(dict(status=result['status'],sha256=digest)))
