"""Freeze light balanced requests only after synchronized actual video PASS."""
import ast
import json
import shutil
import subprocess
import sys
import m351_workflow as w
import m369_component_checks
import m369_collect
import m369_prepare_draft
OLD=w.BASE/'candidates/M368-staged-video-03'
PKG=w.BASE/'candidates/M369-light-video-01'
OUT=w.BASE/'runs/M369-light-video-support-01'


def main():
    if PKG.exists() or OUT.exists():raise RuntimeError('Immutable preparation exists')
    prior=w.BASE/'runs/M368-video-closure-02/RESULT.json';numeric=json.loads(prior.read_text(encoding='utf-8'))
    if numeric['status']!='PASS_INDEPENDENT_VIDEO_CAPACITY_AND_NUMERICS' or not numeric['numerical_pass']:raise RuntimeError('Actual video prerequisite absent')
    for name in ('CURRENT_STATE.md','docsMILESTONES.md','deployment/mage_vl4b/BOARD_GATE_RESULT.json'):assert w.sha(prior) in (w.ROOT/name).read_text(encoding='utf-8')
    m369_prepare_draft.main();checks=m369_component_checks.checks();negatives=m369_collect.self_test()
    PKG.mkdir()
    names=('measurement.py','owned_buffer_release.py','m363_package_identity.py','m363_observers.py','m341_build_id_gate.py','frozen_video_identity.py','memory_lifecycle.py','ps_slot_capacity.py','m120_board_common.py','m120_board_env_preflight.py','board_safety.py','m363_tokenizer_once.py','SOURCE_CLOSURE.json','M348_SOURCE_IDENTITIES.json','M357_COMPARE_PREREQUISITE.json','HARDWARE_CLOSURE.json','STAGE_PREREQUISITE.json','VISUAL_EXPECTED.json','VIDEO_EXPECTED.json','VIDEO_BUDGET.json','m368_stage_policy.py','m368_video_contract.py')
    for name in names:shutil.copyfile(OLD/name,PKG/name)
    shutil.copyfile(OLD/'m368_head_observer.py',PKG/'m366_head_observer.py')
    shutil.copyfile(prior,PKG/'NUMERIC_PREREQUISITE.json')
    for name in ('m369_light_video_gate.py','m369_light_policy.py','m369_trials.py'):shutil.copyfile(w.HERE/name,PKG/name)
    export=(OLD/'m368_export_result.py').read_text(encoding='utf-8').replace('M368','M369').replace("(Path('/home/ubuntu/m368_staged_video_02')/case/'load-memory.json')","(Path('/home/ubuntu/m369_light_video_01')/'load-memory.json')").replace('independent-fixed159-video-capacity-diagnostic','balanced-fixed159-video-light-performance').replace('import sys','import sys\nimport time').replace("for i,p in enumerate(chunks):print(f'M369_RESULT_CHUNK={i}/{len(chunks)}:'+base64.b64encode(p).decode('ascii'),flush=True)","for i,p in enumerate(chunks):\n        print(f'M369_RESULT_CHUNK={i}/{len(chunks)}:'+base64.b64encode(p).decode('ascii'),flush=True)\n        time.sleep(.04)")
    w.atomic(PKG/'m369_export_result.py',export.encode())
    runner='''#!/usr/bin/env bash
set -euo pipefail
[[ $EUID == 0 ]] || exit 65
task_dir=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)
task_python=/usr/local/share/pynq-venv/bin/python
[[ $# == 3 && $3 == B1 ]] || exit 64
if [[ $2 == Collect ]]; then "$task_python" -B "$task_dir/m369_export_result.py" "$3"; exit 0; fi
[[ $2 == Run && ${M369_ENABLE_LIGHT_VIDEO:-0} == 1 ]] || exit 66
[[ ! -e /home/ubuntu/m369_light_video_01 ]] || exit 67
export XILINX_XRT=/usr TMPDIR=/dev/shm PATH=/usr/local/share/pynq-venv/bin:$PATH
set +e
"$task_python" -B "$task_dir/m369_light_video_gate.py" "$1" "$3" --enable-staged-video
task_gate_rc=$?
"$task_python" -B "$task_dir/m369_export_result.py" "$3"
task_export_rc=$?
set -e
echo "M369_DONE case=$3 gate_rc=$task_gate_rc export_rc=$task_export_rc"
if [[ $task_gate_rc != 0 ]]; then exit "$task_gate_rc"; fi
exit "$task_export_rc"
'''
    w.atomic(PKG/'run_m369_light_video.sh',runner.encode())
    assembly='''import hashlib,json,shutil,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parent
OLD=Path('/home/ubuntu/m368_staged_video_candidate_03')
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main(expected):
    if sha(ROOT/'PACKAGE_MANIFEST.json')!=expected:raise RuntimeError('Manifest differs')
    if sha(OLD/'PACKAGE_MANIFEST.json')!='f5937684306cd0ce40683a9bc46097b69cc7a9c7625bf208883eaada8071fb66':raise RuntimeError('Prior identity differs')
    new=json.loads((ROOT/'PACKAGE_MANIFEST.json').read_text(encoding='utf-8'));old=json.loads((OLD/'PACKAGE_MANIFEST.json').read_text(encoding='utf-8'))
    bysha={r['sha256']:r for r in old['files']}
    for row in new['files']:
        if '/' in row['path'] or chr(92) in row['path']:raise RuntimeError('Flat whitelist')
        target=ROOT/row['path']
        if not target.exists():
            source=bysha.get(row['sha256'])
            if source is None:raise RuntimeError('Missing new payload')
            p=OLD/source['path']
            if sha(p)!=row['sha256'] or p.stat().st_size!=row['bytes']:raise RuntimeError('Prior payload differs')
            shutil.copyfile(p,target)
        if sha(target)!=row['sha256'] or target.stat().st_size!=row['bytes']:raise RuntimeError('Payload differs')
    if {p.name for p in ROOT.iterdir()}!={r['path'] for r in new['files']}|{'PACKAGE_MANIFEST.json'}:raise RuntimeError('Whitelist differs')
    print('M369_ALL_PAYLOAD_SHA_VERIFIED_NO_GATE')
if __name__=='__main__':main(sys.argv[1])
'''
    w.atomic(PKG/'m369_assemble.py',assembly.encode())
    rows=[dict(path=p.name,bytes=p.stat().st_size,sha256=w.sha(p)) for p in sorted(PKG.iterdir())]
    w.atomic(PKG/'SHA256SUMS',''.join(r['sha256']+'  '+r['path']+'\n' for r in rows).encode())
    rows.append(dict(path='SHA256SUMS',bytes=(PKG/'SHA256SUMS').stat().st_size,sha256=w.sha(PKG/'SHA256SUMS')))
    w.atomic(PKG/'PACKAGE_MANIFEST.json',w.encoded(dict(schema='m369-light-balanced-fixed159-video-v1',files=rows,file_count=len(rows),total_bytes=sum(r['bytes'] for r in rows))))
    closure=json.loads((OLD/'SOURCE_CLOSURE.json').read_text(encoding='utf-8'))
    release=w.ROOT/'release_staging/kv260-mage-vl-4b-prebuilt-install-20260926-v7'
    for row in closure['files']:assert w.sha(release/row['path'])==row['sha256']
    hw=json.loads((OLD/'HARDWARE_CLOSURE.json').read_text(encoding='utf-8'))
    for row in hw['prerequisites']:assert w.sha(w.ROOT/row['path'])==row['sha256']
    trees={p.stem:ast.parse(p.read_text(encoding='utf-8'),feature_version=(3,10)) for p in PKG.glob('*.py')}
    allowed=set(sys.stdlib_module_names)|set(closure['modules'])|{'numpy','pynq','tokenizers','m276_m254_video_server'};missing=[]
    for module,tree in trees.items():
        for node in ast.walk(tree):
            names=[a.name.split('.')[0] for a in node.names] if isinstance(node,ast.Import) else ([node.module.split('.')[0]] if isinstance(node,ast.ImportFrom) and node.module else [])
            missing.extend((module,n) for n in names if n not in trees and n not in allowed)
    assert not missing,missing
    assert not list(PKG.rglob('*.pyc')) and not list(PKG.rglob('__pycache__'))
    ps='C:/Users/30429/.cache/codex-runtimes/codex-primary-runtime/dependencies/native/powershell/pwsh.exe'
    c=subprocess.run([ps,'-NoProfile','-File',str(w.HERE/'m369_control.ps1'),'-Mode','SelfTest'],capture_output=True,text=True,encoding='utf-8')
    assert c.returncode==0 and 'M369_CONTROL_SELFTEST_PASS' in c.stdout,c.stdout+c.stderr
    r=dict(status='PASS_OFFLINE_LIGHT_VIDEO_CONTROL',manifest_sha256=w.sha(PKG/'PACKAGE_MANIFEST.json'),numeric_closure_sha256=w.sha(prior),checks=checks,collector_negative_checks=negatives,python310_syntax=True,source_closure_missing=missing,same_sha_hardware_evidence_reused=True,head_support_sha256='5cbc726714c01d38339e823fa3da382f2e292f0dc21d2b7f00e98f5df81f5379',fake_model_MMIO_memory_explicit=True,order='ABBABAAB',request_hashing=False,post_request_exact_checks=True,board_executed=False,performance_pass=False,formal_promotion_allowed=False)
    w.atomic(OUT/'RESULT.json',w.encoded(r),immutable=True);digest=w.sha(OUT/'RESULT.json')
    w.sync('latest_m369_light_video_support',dict(status=r['status'],sha256=digest,result=(OUT/'RESULT.json').relative_to(w.ROOT).as_posix(),manifest_sha256=r['manifest_sha256']),f'## M369 轻量交错视频性能门禁准备\n\n支持SHA `{digest}`，视频数值前级SHA `{w.sha(prior)}`；复用同SHA硬件/实际head证据。原完整请求计时，稳定A/候选B的ABBABAAB顺序，PS原缓存一次预热保留；SHA仅请求后。实际冻结stream控制明确fake模型/MMIO/内存检查通过，离线不证明板端性能。下一步执行一次8请求测量，保留全部样本并离线裁决。')
    print(json.dumps(r))


if __name__=='__main__':main()
