"""Freeze real-video identity/recursive source closure after M344 synchronization."""
import ast
import copy
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import sys
sys.dont_write_bytecode = True
import numpy as np
ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent
BASE = ROOT / 'deployment/mage_vl4b/optimization_v1'
PRIOR_SHA = '897bb817d6bd2a12f5de5437bb015541210f86c297c85456bc570586d479673a'


def sha(path): return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    package = BASE / 'candidates/M345-fixed-video-01'; run = BASE / 'runs/M345-fixed-video-preparation-01'
    if package.exists() or run.exists(): raise RuntimeError('Immutable preparation exists')
    recovery = {}
    for name in ('CURRENT_STATE.md','docsMILESTONES.md','DEPLOYMENT_OPERATION_MISTAKES_REVIEW.md','deployment/mage_vl4b/BOARD_GATE_RESULT.json'):
        raw = (ROOT/name).read_bytes(); raw.decode('utf-8-sig')
        recovery[name] = dict(bytes=len(raw),sha256=hashlib.sha256(raw).hexdigest())
    prior = BASE / 'runs/M344-fixed-text-board-01/BOARD_RESULT.json'
    proof = json.loads(prior.read_text(encoding='utf-8'))
    board = json.loads((ROOT/'deployment/mage_vl4b/BOARD_GATE_RESULT.json').read_text(encoding='utf-8'))
    if sha(prior) != PRIOR_SHA or proof['status'] != 'PASS' or proof['unsafe_buffers_retained'] or not proof['safe_buffers_released']:
        raise RuntimeError('Exact safely completed M344 prerequisite differs')
    if not all(proof[k] for k in ('direct_bitwise_logits_equal','direct_bitwise_72_kv_equal')) or not all(proof['exact_comparison'].values()):
        raise RuntimeError('M344 exact numerical evidence differs')
    if board['latest_m344_fixed_text']['sha256'] != PRIOR_SHA or not all(PRIOR_SHA in (ROOT/n).read_text(encoding='utf-8') for n in ('CURRENT_STATE.md','docsMILESTONES.md')):
        raise RuntimeError('Three authoritative records not synchronized')
    summary = BASE / 'runs/M344-fixed-text-board-01/SUMMARY.json'
    summary_data = json.loads(summary.read_text(encoding='utf-8'))
    if summary_data['sha256'] != PRIOR_SHA or summary_data['status'] != 'PASS' or summary_data['exact'] != proof['exact_comparison']:
        raise RuntimeError('Exact-byte predecessor summary differs')
    previous = BASE / 'candidates/M344-fixed-text-01'
    frozen_source = (BASE/'candidates/M339-prefill-profile-04/run_fixed_video_profile.py').read_text(encoding='utf-8')
    tree = ast.parse(frozen_source)
    constants = ('ADDON','RELEASE','M277_SHA','FRAMES','STACK_SHA','OMITTED_BOUNDARY_DOCS')
    pieces = ['import ast\nimport hashlib\nimport json\nfrom pathlib import Path\nVARIANT = "baseline"']
    for node in tree.body:
        if isinstance(node,ast.Assign) and any(isinstance(t,ast.Name) and t.id in constants for t in node.targets):
            pieces.append(ast.get_source_segment(frozen_source,node))
        if isinstance(node,ast.FunctionDef) and node.name in ('digest','module_paths','verify_m277_release_subset'):
            pieces.append(ast.get_source_segment(frozen_source,node))
    identity = '\n\n'.join(pieces)+'\n'; namespace = {}; exec(identity,namespace)
    directories = [p.relative_to(namespace['RELEASE']).as_posix() for p in namespace['module_paths']()]
    local_dirs = [ROOT/d for d in directories if d != 'runtime_site']
    if not all(p.is_dir() for p in local_dirs): raise RuntimeError('Exact local module directories missing')
    modules, files, unresolved = {}, {}, set()
    queue = ['m276_m254_video_server','m277_fixed_window_gate','reserved_ddr_pool']
    while queue:
        name = queue.pop()
        if name in modules or name in unresolved: continue
        path = next((d/(name+'.py') for d in local_dirs if (d/(name+'.py')).is_file()),None)
        if path is None:
            unresolved.add(name); continue
        relative = path.relative_to(ROOT).as_posix(); modules[name] = relative
        files[relative] = dict(path=relative,bytes=path.stat().st_size,sha256=sha(path))
        source = path.read_text(encoding='utf-8'); module_tree = ast.parse(source)
        for node in ast.walk(module_tree):
            if isinstance(node,ast.Import): queue.extend(a.name.split('.')[0] for a in node.names)
            if isinstance(node,ast.ImportFrom) and node.module and not node.level: queue.append(node.module.split('.')[0])
    missing_project = sorted(n for n in unresolved if n.startswith(('m2','m1','video_','board_','ps_','contract_','keyframe_','variable_','reserved_')))
    if missing_project: raise RuntimeError('Recursive project import closure missing: '+repr(missing_project))
    expected = json.loads((previous/'SOURCE_CLOSURE.json').read_text(encoding='utf-8'))
    for n in ('board_runtime','m238_prefill_runtime','m241_video_language_runtime'):
        if modules[n] != expected['modules'][n]: raise RuntimeError('Final resolution differs from exact verified M238/M241')
    staged = ROOT / 'release_staging/kv260-mage-vl-4b-prebuilt-install-20260926-v7'
    for relative in ('scripts/preflight.py','configs/deployment.example.json'):
        path = staged/relative; files[relative] = dict(path=relative,bytes=path.stat().st_size,sha256=sha(path))
    closure = dict(module_dirs=directories,modules=modules,files=list(files.values()),
                   recursive_missing_project=missing_project,declared_external_imports=sorted(unresolved),
                   entry_import='Actual board final-order import before model/overlay; Windows recursive source/AST only')
    source = (HERE/'m345_fixed_video_gate.py').read_text(encoding='utf-8'); test_ns = {'np':np,'hashlib':hashlib}
    for node in ast.parse(source).body:
        if isinstance(node,ast.FunctionDef) and node.name in ('tensor','exact_array','check_call_contract','validate_stream'):
            exec(ast.get_source_segment(source,node),test_ns)
    attempts = [dict(layer=0 if i<770 else None,attempted_shifts=[6],selected_shift=6) for i in range(778)]
    row = dict(scale_attempts=attempts,logical_calls=778,host_calls=778,retry_count=0,retry_launches=0,nonfinite_detections=0,logical_expected_macros=123)
    test_ns['check_call_contract'](row,123)
    row['scale_attempts'][0].update(attempted_shifts=[6,5],selected_shift=5)
    row['scale_attempts'][-1].update(attempted_shifts=[6,5],selected_shift=5)
    row.update(host_calls=780,retry_count=2,retry_launches=1,nonfinite_detections=1)
    test_ns['check_call_contract'](row,123)
    rejected=[]
    for name,edit in [('physical_count',dict(host_calls=779)),('pipeline_count',dict(retry_launches=2)),('macro_count',dict(logical_expected_macros=124))]:
        bad=copy.deepcopy(row); bad.update(edit)
        try: test_ns['check_call_contract'](bad,123)
        except RuntimeError: rejected.append(name)
        else: raise AssertionError('Invalid call contract accepted')
    assert not test_ns['exact_array'](np.array([0.0],np.float32),np.array([-0.0],np.float32))
    x=np.array([1.0],np.float32); y=x.copy(); y.view(np.uint32)[0] ^= 1
    assert not test_ns['exact_array'](x,y)
    frame_contract=dict(files=namespace['FRAMES'],ordered_tensor_sha256=namespace['STACK_SHA'],shape=[4,448,448,3],dtype='uint8',
        selected_frame_indices=[3],source_frames_used=1,views=2,visual_tokens=98,prompt_tokens=159,decode_calls=0,
        exact_outputs=['159x2560 video hidden','151936 logits','36 K and 36 V','all original family bytes and retry contracts'],performance_pass=False)
    # All local functions, collector and controller checks precede immutable freeze/transfer.
    for name in ('m345_fixed_video_gate.py','m345_collect_video.py'):
        ast.parse((HERE/name).read_text(encoding='utf-8'))
    checked=subprocess.run([sys.executable,'-B',str(HERE/'m345_collect_video.py'),'--self-test'],capture_output=True,text=True,encoding='utf-8')
    if checked.returncode: raise RuntimeError(checked.stdout+checked.stderr)
    package.mkdir(parents=True); run.mkdir(parents=True)
    for name in recovery: shutil.copyfile(ROOT/name,run/(Path(name).name+'.before'))
    for name in ('m341_build_id_gate.py','measurement.py','board_safety.py','m120_board_common.py','m120_board_env_preflight.py','HARDWARE_CLOSURE.json','weight_prefetch.py'):
        shutil.copyfile(previous/name,package/name)
    shutil.copyfile(summary,package/'FIXED_TEXT_PREREQUISITE.json')
    shutil.copyfile(HERE/'m345_fixed_video_gate.py',package/'m345_fixed_video_gate.py')
    (package/'frozen_video_identity.py').write_text(identity,encoding='utf-8',newline='\n')
    for name,payload in (('SOURCE_CLOSURE.json',closure),('INPUT_CONTRACT.json',frame_contract)):
        (package/name).write_text(json.dumps(payload,indent=2)+'\n',encoding='utf-8',newline='\n')
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
  /usr/local/share/pynq-venv/bin/python3 -B "$package_dir/m345_fixed_video_gate.py" "$manifest_sha"
gate_rc=$?
set -e
printf 'M345_VIDEO_DONE gate_rc=%s\\n' "$gate_rc"
exit "$gate_rc"
'''
    (package/'run_m345_video.sh').write_text(runner,encoding='utf-8',newline='\n')
    items=[dict(path=p.name,bytes=p.stat().st_size,sha256=sha(p)) for p in sorted(package.iterdir())]
    (package/'SHA256SUMS').write_text(''.join(i['sha256']+'  '+i['path']+'\n' for i in items),encoding='utf-8',newline='\n')
    items.append(dict(path='SHA256SUMS',bytes=(package/'SHA256SUMS').stat().st_size,sha256=sha(package/'SHA256SUMS')))
    manifest=dict(schema='tellme-m345-fixed-video-weight-prefetch-v1',files=items,file_count=len(items),total_bytes=sum(i['bytes'] for i in items),
        hardware_changed=False,performance_pass=False,prerequisite_raw_sha256=PRIOR_SHA,prerequisite_summary_sha256=sha(summary))
    (package/'PACKAGE_MANIFEST.json').write_text(json.dumps(manifest,indent=2)+'\n',encoding='utf-8',newline='\n')
    result=dict(status='PASS_OFFLINE_VIDEO_PREPARATION',recovery_read=recovery,files=len(items),bytes=manifest['total_bytes'],
        manifest_sha256=sha(package/'PACKAGE_MANIFEST.json'),recursive_modules=len(modules),recursive_missing_project=missing_project,
        checks=dict(complete_778_retry_contract=True,invalid_counts_rejected=rejected,signed_zero_and_one_bit_rejected=True,
            collector_utf8_sha_chunks_rejection=checked.stdout.strip(),exact_original_m238_m241_resolution=True),
        rejected_attempts=[],evidence_level='L0',hardware_gate_run=False,performance_pass=False)
    (run/'RESULT.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8',newline='\n')
    print(json.dumps(result))


if __name__ == '__main__': main()
