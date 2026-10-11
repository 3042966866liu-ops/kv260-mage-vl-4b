"""Clean load-only diagnostic package, fail-closed prerequisite/source checks."""
import ast
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import sys
sys.dont_write_bytecode=True
ROOT=Path(__file__).resolve().parents[2]
HERE=Path(__file__).resolve().parent
BASE=ROOT/'deployment/mage_vl4b/optimization_v1'
PRIOR_SHA='b149cf6d4e031628c4ff43c99f6e4579575a64598ee55d80e35c2f7ff48e8fd4'


def sha(path):
    h=hashlib.sha256()
    with path.open('rb') as f:
        for block in iter(lambda:f.read(4<<20),b''): h.update(block)
    return h.hexdigest()


def main():
    package=BASE/'candidates/M346-load-memory-01'; run=BASE/'runs/M346-load-memory-preparation-01'
    if package.exists() or run.exists(): raise RuntimeError('Immutable preparation exists')
    recovery={}
    for name in ('CURRENT_STATE.md','docsMILESTONES.md','DEPLOYMENT_OPERATION_MISTAKES_REVIEW.md','deployment/mage_vl4b/BOARD_GATE_RESULT.json'):
        raw=(ROOT/name).read_bytes(); full_text=raw.decode('utf-8-sig')
        recovery[name]=dict(bytes=len(raw),lines=len(full_text.splitlines()),sha256=hashlib.sha256(raw).hexdigest())
    prior=BASE/'runs/M345-fixed-video-board-01/BOARD_RESULT.json'; result=json.loads(prior.read_text(encoding='utf-8'))
    board=json.loads((ROOT/'deployment/mage_vl4b/BOARD_GATE_RESULT.json').read_text(encoding='utf-8'))
    if sha(prior)!=PRIOR_SHA or result['status']!='FAIL' or not result['safe_buffers_released'] or result['unsafe_buffers_retained'] or result.get('prefetch') is not None:
        raise RuntimeError('Exact safely closed CMA failure differs')
    if board['latest_m345_fixed_video']['sha256']!=PRIOR_SHA or not all(PRIOR_SHA in (ROOT/n).read_text(encoding='utf-8') for n in ('CURRENT_STATE.md','docsMILESTONES.md')):
        raise RuntimeError('CMA failure not synchronized in all three records')
    closed=BASE/'runs/M345-failure-closure-01/RESULT.json'
    if sha(closed)!='a53c5eaa8c190c91a95f3fb5674f30a1bbce02057751f4073c31b4bee9fdcf41': raise RuntimeError('Failure closure identity differs')
    previous=BASE/'candidates/M345-fixed-video-01'
    hardware=json.loads((previous/'HARDWARE_CLOSURE.json').read_text(encoding='utf-8'))
    if len(hardware['checked'])!=47 or hardware['errors']: raise RuntimeError('47 unchanged hardware items required')
    for row in hardware['checked']:
        file=ROOT/row.get('recovered_exact_snapshot',row['path'])
        expected=row.get('recovered_sha256',row['expected_sha256'])
        expected_bytes=row.get('historical_bytes',row['bytes'])
        if file.stat().st_size!=expected_bytes or sha(file)!=expected: raise RuntimeError('Hardware evidence drift: '+str(file))
    for name,row in hardware['evidence_documents'].items():
        if sha(ROOT/'deployment/mage_vl4b'/name)!=row['sha256']: raise RuntimeError('Hardware evidence document drift')
    closure=json.loads((previous/'SOURCE_CLOSURE.json').read_text(encoding='utf-8'))
    staged=ROOT/'release_staging/kv260-mage-vl-4b-prebuilt-install-20260926-v7'
    for row in closure['files']:
        file=ROOT/row['path']
        if not file.exists(): file=staged/row['path']
        if file.stat().st_size!=row['bytes'] or sha(file)!=row['sha256']: raise RuntimeError('Original recursive source drift')
    source=(HERE/'m346_load_memory_probe.py').read_text(encoding='utf-8'); tree=ast.parse(source)
    banned={'stream','prefill','decode','forward','_execute','_launch_once','_launch_prepacked','_stage','language_family_many','lm_head'}
    def serialization_decode(node):
        receiver=node.func.value
        return (node.func.attr=='decode' and isinstance(receiver,ast.Call) and isinstance(receiver.func,ast.Attribute)
                and receiver.func.attr=='b64encode' and isinstance(receiver.func.value,ast.Name) and receiver.func.value.id=='base64')
    bad=[node.func.attr for node in ast.walk(tree) if isinstance(node,ast.Call) and isinstance(node.func,ast.Attribute)
         and node.func.attr in banned and not serialization_decode(node)]
    if bad: raise RuntimeError('Load-only script invokes forbidden computation: '+repr(bad))
    namespace={}
    for node in tree.body:
        if isinstance(node,ast.Assign) and any(isinstance(t,ast.Name) and t.id in ('REQUIRED_FREE','BLOCKED_BOARD_METHODS') for t in node.targets):
            exec(ast.get_source_segment(source,node),namespace)
        if isinstance(node,ast.FunctionDef) and node.name in ('forbid','memory_eligibility'): exec(ast.get_source_segment(source,node),namespace)
    blocked=[]
    methods=list(namespace['BLOCKED_BOARD_METHODS'])+['engine.stream','vision.__call__','vision.tower.forward','language.prefill','language.decode','language._family']
    for name in methods:
        try: namespace['forbid'](name,blocked)()
        except RuntimeError: pass
        else: raise AssertionError('Forbidden inference accepted')
    assert blocked==methods
    required=namespace['REQUIRED_FREE']; eligibility=namespace['memory_eligibility']
    assert required==94961664
    assert eligibility({'system_bytes':{'CmaFree':required}})['meets_load_only_threshold']
    assert not eligibility({'system_bytes':{'CmaFree':required-1}})['meets_load_only_threshold']
    # Known original constructors must contain no transaction or forward calls.
    audited=[]
    for name in ('board_runtime','m230_prefill_runtime','m231_prefill_runtime','m236_prefill_runtime','m238_prefill_runtime','m241_video_language_runtime'):
        path=ROOT/closure['modules'][name]
        for node in ast.walk(ast.parse(path.read_text(encoding='utf-8'))):
            if isinstance(node,ast.FunctionDef) and node.name=='__init__':
                calls=[n.func.attr for n in ast.walk(node) if isinstance(n,ast.Call) and isinstance(n.func,ast.Attribute) and n.func.attr in banned|{'transfer','write'}]
                if calls: raise RuntimeError('Original constructor submits transaction: '+name+repr(calls))
        audited.append(name)
    collector=subprocess.run([sys.executable,'-B',str(HERE/'m346_collect_memory.py'),'--self-test'],capture_output=True,text=True,encoding='utf-8')
    if collector.returncode: raise RuntimeError(collector.stdout+collector.stderr)
    control=subprocess.run([r'C:\Users\30429\.cache\codex-runtimes\codex-primary-runtime\dependencies\native\powershell\pwsh.exe',
        '-NoProfile','-File',str(HERE/'m346_run_and_collect.ps1'),'-SelfTest'],capture_output=True,text=True,encoding='utf-8')
    if control.returncode: raise RuntimeError(control.stdout+control.stderr)
    package.mkdir(parents=True); run.mkdir(parents=True)
    for name in recovery: shutil.copyfile(ROOT/name,run/(Path(name).name+'.before'))
    for name in ('m341_build_id_gate.py','measurement.py','board_safety.py','m120_board_common.py','m120_board_env_preflight.py',
                 'HARDWARE_CLOSURE.json','frozen_video_identity.py','SOURCE_CLOSURE.json'):
        shutil.copyfile(previous/name,package/name)
    shutil.copyfile(closed,package/'M345_FAILURE_PREREQUISITE.json')
    for name in ('m346_load_memory_probe.py','memory_lifecycle.py'): shutil.copyfile(HERE/name,package/name)
    runner='''#!/usr/bin/env bash
set -euo pipefail
package_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$package_dir"
manifest_sha=${1:?exact manifest SHA required}
printf '%s  PACKAGE_MANIFEST.json\\n' "$manifest_sha" | sha256sum -c -
sha256sum -c SHA256SUMS
sudo -n true
set +e
sudo -n env XILINX_XRT=/usr TMPDIR=/dev/shm PATH=/usr/local/share/pynq-venv/bin:/usr/local/bin:/usr/bin:/bin PYTHONDONTWRITEBYTECODE=1 TRANSFORMERS_OFFLINE=1 HF_HUB_OFFLINE=1 \\
  /usr/local/share/pynq-venv/bin/python3 -B "$package_dir/m346_load_memory_probe.py" "$manifest_sha"
gate_rc=$?
set -e
printf 'M346_MEMORY_DONE gate_rc=%s\\n' "$gate_rc"
exit "$gate_rc"
'''
    (package/'run_m346_memory.sh').write_text(runner,encoding='utf-8',newline='\n')
    items=[dict(path=p.name,bytes=p.stat().st_size,sha256=sha(p)) for p in sorted(package.iterdir())]
    (package/'SHA256SUMS').write_text(''.join(i['sha256']+'  '+i['path']+'\n' for i in items),encoding='utf-8',newline='\n')
    items.append(dict(path='SHA256SUMS',bytes=(package/'SHA256SUMS').stat().st_size,sha256=sha(package/'SHA256SUMS')))
    manifest=dict(schema='tellme-m346-load-memory-only-v1',files=items,file_count=len(items),total_bytes=sum(i['bytes'] for i in items),
        hardware_changed=False,numerical_pass=False,performance_pass=False,model_forward_allowed=False,prior_board_sha256=PRIOR_SHA)
    (package/'PACKAGE_MANIFEST.json').write_text(json.dumps(manifest,indent=2)+'\n',encoding='utf-8',newline='\n')
    prep=dict(status='PASS_OFFLINE_LOAD_ONLY_PREPARATION',recovery_read=recovery,files=len(items),bytes=manifest['total_bytes'],manifest_sha256=sha(package/'PACKAGE_MANIFEST.json'),
        checks=dict(unchanged_hardware_items=47,source_modules=len(closure['modules']),forbidden_calls_in_probe=bad,blocked_entrypoints_tested=methods,
            original_constructor_no_transaction_audit=audited,cma_threshold_and_one_byte_below_checked=True,
            collector=collector.stdout.strip(),controller=control.stdout.strip()),
        evidence_level='L0',board_run=False,model_forward=False,numerical_pass=False,performance_pass=False,
        rejected_attempts=['Offline generic .decode call audit initially rejected base64.b64encode(...).decode serialization; narrowed only that exact serialization receiver, no model decode permitted; before package/transfer/board'])
    (run/'RESULT.json').write_text(json.dumps(prep,indent=2)+'\n',encoding='utf-8',newline='\n')
    print(json.dumps(prep))


if __name__=='__main__': main()
