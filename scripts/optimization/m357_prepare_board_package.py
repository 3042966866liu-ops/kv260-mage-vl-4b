"""Create a clean, closed candidate package only after full-shell PASS."""
import ast
import json
import shutil
from pathlib import Path
import m351_workflow as w
from m357_transfer import verify_directory
ROOT=Path(__file__).resolve().parents[2]
HERE=Path(__file__).resolve().parent
BASE=ROOT/'deployment/mage_vl4b/optimization_v1'
PKG=BASE/'candidates/M357-private-activation-01'
BOOT=BASE/'candidates/M357-transfer-bootstrap-01'
def manifest(directory,schema):
    rows=[dict(path=p.relative_to(directory).as_posix(),bytes=p.stat().st_size,sha256=w.sha(p)) for p in sorted(directory.rglob('*')) if p.is_file()]
    value=dict(schema=schema,files=rows,file_count=len(rows),total_bytes=sum(r['bytes'] for r in rows))
    w.atomic(directory/'PACKAGE_MANIFEST.json',w.encoded(value),immutable=True)
    sha=w.sha(directory/'PACKAGE_MANIFEST.json');verify_directory(directory,sha);return value,sha
def main():
    proof=[]
    names=['M357-activation-bank-preparation-01','M357-activation-bank-csim-01','M356-stable-q-rtl-02',
        'M357-candidate-q-rtl-02','M357-max-fifo-rtl-03','M357-timeout-rtl-01','M357-core-ooc-01',
        'M357-full-shell-02','M357-hwh-abi-01','M357-board-fixture-repair-01','M357-board-support-preparation-04']
    for name in names:
        p=BASE/'runs'/name/'RESULT.json'
        r=json.loads(p.read_text(encoding='utf-8'));digest=w.sha(p)
        assert r['status'].startswith(('PASS_','PREPARED_','CORRECTED_')),(name,r['status'])
        for n in ('CURRENT_STATE.md','docsMILESTONES.md','deployment/mage_vl4b/BOARD_GATE_RESULT.json'):
            assert digest in (ROOT/n).read_text(encoding='utf-8-sig'),(name,n)
        proof.append(dict(path=p.relative_to(ROOT).as_posix(),sha256=digest,status=r['status']))
    shell=json.loads((BASE/'runs/M357-full-shell-02/RESULT.json').read_text(encoding='utf-8'))
    assert shell['status']=='PASS_FULL_SHELL_ROUTED_TIMING' and not shell['errors']
    original=json.loads((BASE/'runs/M357-activation-bank-preparation-01/RESULT.json').read_text(encoding='utf-8'))
    assert not original['missing'] and len(original['source_closure'])==13
    for row in original['source_closure']:assert w.sha(ROOT/row['path'])==row['sha256'],'Stable source closure changed'
    assert w.sha(ROOT/'tmp/m357_activation_banks/hls/mage_prefill_m89x_runtime/mage_prefill_m89x_runtime.cpp')==original['candidate_sha256']
    support=json.loads((BASE/'runs/M357-board-support-preparation-04/RESULT.json').read_text(encoding='utf-8'))
    for row in support['files']:assert w.sha(ROOT/row['path'])==row['sha256'],'Support source changed'
    assert not PKG.exists() and not BOOT.exists(),'Existing candidate staging; inspect only'
    source=BASE/'candidates/M355-device-phase-01'
    copies={name:source/name for name in ('m341_build_id_gate.py','m120_board_common.py','m120_board_env_preflight.py','board_safety.py','owned_buffer_release.py','measurement.py')}
    copies.update({name:HERE/name for name in ('m357_board_probe.py','m357_export_result.py','m357_gate_runner.sh')})
    copies['m357_completion_observer.py']=ROOT/'tmp/m357_board_support_01/m357_completion_observer.py'
    fixture=ROOT/'tmp/m357_board_fixture_02'
    for p in fixture.iterdir():
        if p.is_file():copies[p.name]=p
    assert w.sha(fixture/'BOARD_CASES.json')=='e1bbd5e483090543244c40aafddd2ca698dbe62fea60389747ea04542c2eed66'
    hwh=json.loads((BASE/'runs/M357-hwh-abi-01/RESULT.json').read_text(encoding='utf-8'))
    copies['overlay/m120_m89x2_t32.hwh']=ROOT/hwh['candidate_path']
    copies['overlay/m120_m89x2_t32.bit']=ROOT/'tmp/m357_shell_01/out/m357_t32.bit'
    for row in shell['artifacts']:assert w.sha(ROOT/row['path'])==row['sha256']
    assert w.sha(copies['overlay/m120_m89x2_t32.hwh'])==shell['matching_hwh_sha256']
    for name,p in copies.items():
        assert p.is_file() and not p.is_symlink()
        if name.endswith('.py'):ast.parse(p.read_text(encoding='utf-8'),feature_version=(3,10))
    PKG.mkdir(parents=True)
    for name,p in copies.items():
        target=PKG/name;target.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(p,target)
    for row in proof:
        p=ROOT/row['path'];target=PKG/'evidence'/p.parent.name/p.name;target.parent.mkdir(parents=True);shutil.copyfile(p,target)
    closure=dict(status='PASS_ALL_NEW_CIRCUIT_PREREQUISITES',build_id='0x4D333537',stable_build_id='0x4D395832',
        change='Four private read-only activation/scale banks; original loader copies before descriptors. No math, weights, descriptor, FIFO or merge changes.',
        prerequisites=proof,stable_rollback_intact=True,original_source_closure_unchanged=True,board_pass=False,model_pass=False,video_pass=False,promoted=False)
    w.atomic(PKG/'HARDWARE_CLOSURE.json',w.encoded(closure),immutable=True)
    package,digest=manifest(PKG,'m357-private-activation-candidate-v1')
    transport_rows=[dict(path='PACKAGE_MANIFEST.json',bytes=(PKG/'PACKAGE_MANIFEST.json').stat().st_size,sha256=digest)]+package['files']
    transport=dict(schema='m357-specific-peer-transfer-v1',package_manifest_sha256=digest,files=transport_rows,
        file_count=len(transport_rows),total_bytes=sum(r['bytes'] for r in transport_rows))
    BOOT.mkdir(parents=True);shutil.copyfile(HERE/'m357_transfer.py',BOOT/'m357_transfer.py')
    w.atomic(BOOT/'TRANSPORT_MANIFEST.json',w.encoded(transport),immutable=True)
    runner='''#!/bin/bash
set -euo pipefail
[[ $EUID == 0 ]] || exit 65
[[ $# == 2 ]] || exit 64
task_here=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)
task_action=$1
task_manifest=$2
case "$task_action" in receive|collect) ;; *) exit 64;; esac
exec /usr/local/share/pynq-venv/bin/python -B "$task_here/m357_transfer.py" "$task_action" "$task_here" "$task_manifest"
'''
    w.atomic(BOOT/'run_m357_transfer.sh',runner.encode('utf-8'),immutable=True)
    bootstrap,boot_digest=manifest(BOOT,'m357-readonly-transfer-bootstrap-v1')
    result=dict(status='PREPARED_NEW_CIRCUIT_BOARD_PACKAGE_AFTER_ALL_GATES',build_id='0x4D333537',
        package_path=PKG.relative_to(ROOT).as_posix(),manifest_sha256=digest,package_files=package['file_count'],package_bytes=package['total_bytes'],
        bootstrap_path=BOOT.relative_to(ROOT).as_posix(),bootstrap_manifest_sha256=boot_digest,
        transport_manifest_sha256=w.sha(BOOT/'TRANSPORT_MANIFEST.json'),prerequisites=proof,
        transfer_source_sha256=w.sha(HERE/'m357_transfer.py'),board=False,promoted=False,
        next_step='COM3 shell/same-terminal sudo; manifest-first bootstrap only; bounded specific peer artifact transfer with network restoration proof before BuildID gate')
    ev=BASE/'runs/M357-board-package-preparation-01/RESULT.json';w.atomic(ev,w.encoded(result),immutable=True);sha=w.sha(ev)
    w.sync('M357_board_package_preparation',dict(status=result['status'],sha256=sha,evidence_path=ev.relative_to(ROOT).as_posix(),build_id=result['build_id'],manifest_sha256=digest),
        'M357 新电路全部离线/RTL/整机时序/HWH门禁闭合后准备干净白名单板测包与独立只传输bootstrap；修正OP00完整4096B，默认关闭，无候选上板。证据 '+sha)
    print(json.dumps(result))
if __name__=='__main__':main()
