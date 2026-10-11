"""Closed fresh M441 and exact M357 package; requires all synchronized gates."""
import ast,json,shutil
from m351_workflow import ROOT,BASE,HERE,atomic,encoded,sha,sync
from m441_transfer import verify_directory
PKG=BASE/'candidates/M441-record-load-01'
BOOT=BASE/'candidates/M441-transfer-bootstrap-01'

def manifest(directory,schema):
    rows=[dict(path=p.relative_to(directory).as_posix(),bytes=p.stat().st_size,sha256=sha(p)) for p in sorted(directory.rglob('*')) if p.is_file()]
    r=dict(schema=schema,files=rows,file_count=len(rows),total_bytes=sum(x['bytes'] for x in rows))
    atomic(directory/'PACKAGE_MANIFEST.json',encoded(r),immutable=True);digest=sha(directory/'PACKAGE_MANIFEST.json');verify_directory(directory,digest);return r,digest

def main():
    proofs=[]
    names=['M441-record-pipeline-preparation-02','M441-full-numeric-csim-01',
      'M441-actual-schedule-queue-guard-01','M441-W4-zero-continuation-05',
      'M441-long-B-gate_up-zero-02','M441-boundary-rtl-07','M441-boundary-timeout-07',
      'M441-record-pipeline-core-OOC-closure-01','M441-full-shell-01','M441-hwh-abi-01',
      'M441-board-support-preparation-07','M441-board-support-checks-07','M441-transfer-controls-checks-07']
    for name in names:
        p=BASE/'runs'/name/'RESULT.json';r=json.loads(p.read_bytes());digest=sha(p)
        assert r['status'].startswith(('PASS_','PREPARED_')),(name,r['status'])
        for n in ('CURRENT_STATE.md','docsMILESTONES.md','deployment/mage_vl4b/BOARD_GATE_RESULT.json'):assert digest in (ROOT/n).read_text(encoding='utf-8-sig'),(name,n)
        proofs.append(dict(path=p.relative_to(ROOT).as_posix(),sha256=digest,status=r['status']))
    shell=json.loads((BASE/'runs/M441-full-shell-01/RESULT.json').read_bytes());assert shell['status']=='PASS_FULL_SHELL_ROUTED_TIMING' and not shell['errors']
    for row in shell['artifacts']:assert sha(ROOT/row['path'])==row['sha256']
    source=json.loads((BASE/'runs/M441-record-pipeline-preparation-02/RESULT.json').read_bytes())
    assert source['recursive_inputs'] and not source['missing_headers']
    for row in source['recursive_inputs']+source['files']:assert sha(ROOT/row['path'])==row['sha256']
    support=json.loads((BASE/'runs/M441-board-support-preparation-07/RESULT.json').read_bytes())
    checks=json.loads((BASE/'runs/M441-board-support-checks-07/RESULT.json').read_bytes())
    for row in support['files']+checks['files']:assert sha(ROOT/row['path'])==row['sha256']
    oldprep=json.loads((BASE/'runs/M357-board-package-preparation-01/RESULT.json').read_bytes());old=ROOT/oldprep['package_path']
    verify_directory(old,oldprep['manifest_sha256'])
    oldshell=json.loads((BASE/'runs/M357-full-shell-02/RESULT.json').read_bytes());assert oldshell['status']=='PASS_FULL_SHELL_ROUTED_TIMING'
    oldbit=next(r for r in oldshell['artifacts'] if r['path'].endswith('.bit'))
    assert sha(old/'overlay/m120_m89x2_t32.bit')==oldbit['sha256'];assert sha(old/'overlay/m120_m89x2_t32.hwh')==oldshell['matching_hwh_sha256']
    assert not PKG.exists() and not BOOT.exists(),'Existing staging; inspect only'
    copies={}
    for name in ['m341_build_id_gate.py','m120_board_common.py','m120_board_env_preflight.py','board_safety.py','owned_buffer_release.py','measurement.py']:copies[name]=old/name
    for row in support['files']:
        p=ROOT/row['path']
        if p.name not in ('m441_control07.ps1','m441_transfer.py','m441_transfer_collection.py','m441_board_collection.py','test_m441_board_support07.py','m441_prepare_board_support07.py','m441_freeze_board_support07.py'):copies[p.name]=p
    hwh=json.loads((BASE/'runs/M441-hwh-abi-01/RESULT.json').read_bytes())
    copies['overlay/m120_m89x2_t32.hwh']=ROOT/hwh['candidate_path'];copies['overlay/m120_m89x2_t32.bit']=ROOT/'tmp/m441_shell_01/out/m441_t32.bit'
    copies['baseline/overlay/m120_m89x2_t32.hwh']=old/'overlay/m120_m89x2_t32.hwh';copies['baseline/overlay/m120_m89x2_t32.bit']=old/'overlay/m120_m89x2_t32.bit'
    assert sha(copies['overlay/m120_m89x2_t32.hwh'])==shell['matching_hwh_sha256']
    PKG.mkdir(parents=True)
    for name,p in copies.items():
        assert p.is_file() and not p.is_symlink()
        if name.endswith('.py'):ast.parse(p.read_text(encoding='utf-8'),feature_version=(3,10))
        target=PKG/name;target.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(p,target)
    for row in proofs:
        p=ROOT/row['path'];target=PKG/'evidence'/p.parent.name/p.name;target.parent.mkdir(parents=True);shutil.copyfile(p,target)
    closure=dict(status='PASS_ALL_NEW_CIRCUIT_PREREQUISITES',build_id='0x4D343431',baseline_build_id='0x4D333537',stable_build_id='0x4D395832',prerequisites=proofs,baseline_manifest_sha256=oldprep['manifest_sha256'],baseline_bit_sha256=oldbit['sha256'],change='Per-shard bounded 34-word DATAFLOW stream overlaps sequential current/next W2-W4 record loading with unchanged compute. Original MAC order/math/output and board ABI preserved.',extra_PS_slots=0,extra_CMA_banks=0,next_record_prefetch=True,fixed64MiB_reserve=False,board_pass=False,model_pass=False,video_pass=False,promoted=False)
    atomic(PKG/'HARDWARE_CLOSURE.json',encoded(closure),immutable=True)
    spec,digest=manifest(PKG,'m441-record-load-candidate-v1')
    rows=[dict(path='PACKAGE_MANIFEST.json',bytes=(PKG/'PACKAGE_MANIFEST.json').stat().st_size,sha256=digest)]+spec['files']
    transport=dict(schema='m441-specific-peer-transfer-v1',package_manifest_sha256=digest,files=rows,file_count=len(rows),total_bytes=sum(r['bytes'] for r in rows))
    BOOT.mkdir(parents=True);shutil.copyfile(HERE/'m441_transfer.py',BOOT/'m441_transfer.py');atomic(BOOT/'TRANSPORT_MANIFEST.json',encoded(transport),immutable=True)
    runner='''#!/bin/bash
set -euo pipefail
[[ $EUID == 0 ]] || exit 65
[[ $# == 2 ]] || exit 64
task_here=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)
task_action=$1
task_manifest=$2
case "$task_action" in receive|collect) ;; *) exit 64;; esac
exec /usr/local/share/pynq-venv/bin/python -B "$task_here/m441_transfer.py" "$task_action" "$task_here" "$task_manifest"
'''
    atomic(BOOT/'run_m441_transfer.sh',runner.encode(),immutable=True);bootspec,bootdigest=manifest(BOOT,'m441-transfer-bootstrap-v1')
    r=dict(status='PREPARED_NEW_CIRCUIT_BOARD_PACKAGE_AFTER_ALL_GATES',build_id='0x4D343431',baseline_build_id='0x4D333537',package_path=PKG.relative_to(ROOT).as_posix(),manifest_sha256=digest,package_files=spec['file_count'],package_bytes=spec['total_bytes'],bootstrap_path=BOOT.relative_to(ROOT).as_posix(),bootstrap_manifest_sha256=bootdigest,transport_manifest_sha256=sha(BOOT/'TRANSPORT_MANIFEST.json'),prerequisites=proofs,extra_PS_slots=0,extra_CMA_banks=0,board=False,promoted=False,next_step='COM3 shell/same-terminal sudo once; hash-checked bootstrap and bounded specific-peer transfer, then BuildID only.')
    p=BASE/'runs/M441-board-package-preparation-01/RESULT.json';atomic(p,encoded(r),immutable=True)
    sync('latest_m441_board_package_preparation',dict(status=r['status'],result=p.relative_to(ROOT).as_posix(),sha256=sha(p),build_id=r['build_id'],manifest_sha256=digest,board=False),'## M441 新电路板端隔离包（2026-10-07）\n\nSHA '+sha(p)+'；全前级/整壳时序/HWH/控制负例闭合后干净白名单打包，同包A精确原M357/B新M441，原M9仅恢复。0上传/上板/晋级，0PS槽/CMAbank，不恢复固定64MiB拒绝。下一步COM3 shell/同TTY sudo及有界传输，先Build-ID。')
    print(json.dumps(r))

if __name__=='__main__':main()
