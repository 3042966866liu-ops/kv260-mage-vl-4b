"""Freeze an observation-only fixed-video package from exact M369 bytes."""
import ast
import json
import shutil
import symtable
import sys
from m351_workflow import ROOT, HERE, BASE, sha, atomic, encoded, sync

OLD=BASE/'candidates/M369-light-video-01'
PKG=BASE/'candidates/M375-video-future-wait-01'
OUT=BASE/'runs/M375-video-wait-preparation-01'

def once(source,before,after):
    if source.count(before)!=1:raise RuntimeError('Source anchor differs: '+before)
    return source.replace(before,after)

def main():
    if PKG.exists() or OUT.exists():raise RuntimeError('Preparation exists; inspect rather than repeat')
    board=json.loads((ROOT/'deployment/mage_vl4b/BOARD_GATE_RESULT.json').read_text(encoding='utf-8-sig'))
    prerequisites={}
    for key in ('latest_m375_video_wait_plan','latest_m374_layer_wait_closure','latest_m373_future_wait_closure','latest_m368_video_closure'):
        row=board[key];assert sha(ROOT/row['result'])==row['sha256']
        assert all(row['sha256'] in (ROOT/p).read_text(encoding='utf-8-sig') for p in ('CURRENT_STATE.md','docsMILESTONES.md'))
        prerequisites[key]=row['sha256']
    plan=json.loads((ROOT/board['latest_m375_video_wait_plan']['result']).read_text(encoding='utf-8'))
    assert sha(OLD/'PACKAGE_MANIFEST.json')==plan['base_manifest_sha256']
    manifest=json.loads((OLD/'PACKAGE_MANIFEST.json').read_text(encoding='utf-8'))
    for row in manifest['files']:assert sha(OLD/row['path'])==row['sha256']
    PKG.mkdir()
    skip={'SHA256SUMS','run_m369_light_video.sh','m369_export_result.py','m369_assemble.py','m369_trials.py','m369_light_video_gate.py'}
    for row in manifest['files']:
        if row['path'] not in skip:shutil.copyfile(OLD/row['path'],PKG/row['path'])
    for name in ('m375_video_wait.py','m375_wait_validation.py','m372_future_wait.py','decode_trace.py','m371_profile_summary.py'):
        shutil.copyfile(HERE/name,PKG/name)
    assert sha(PKG/'m372_future_wait.py')=='33f76bc5b910f0b513f86f8cdb81bd68dfcac48220c4f898dd8f0bc6feec3a52'
    prerequisite=ROOT/board['latest_m374_layer_wait_closure']['result']
    shutil.copyfile(prerequisite,PKG/'WAIT_PREREQUISITE.json')
    atomic(PKG/'WAIT_CONTRACT.json',encoded(dict(families=plan['family_contract'],plan_sha256=board['latest_m375_video_wait_plan']['sha256'])))
    trial=(OLD/'m369_trials.py').read_text(encoding='utf-8')
    trial=once(trial,"ORDER='ABBABAAB'","ORDER='B'")
    trial=once(trial,'captured={};stage_ms={};original_prefill=engine.language.prefill;',
        "from m375_video_wait import VideoWaitDiagnostic\n    from m375_wait_validation import validate\n    from m371_profile_summary import pack\n    wait_contract=json.loads((here/'WAIT_CONTRACT.json').read_text(encoding='utf-8'))['families']\n    diagnostic=VideoWaitDiagnostic(engine.language,runtime,wait_contract,enabled=True)\n    captured={};stage_ms={};original_prefill=diagnostic.prefill;")
    trial=once(trial,'        for event,payload in engine.stream(request):events.append((event,payload))',
        "        try:\n            for event,payload in engine.stream(request):events.append((event,payload))\n        finally:\n            if diagnostic.started:\n                try:\n                    wait_report=diagnostic.report()\n                    result['packed_wait_trace']=pack(wait_report)\n                    result['wait_bindings_restored']=wait_report['bindings_restored']\n                except BaseException as observation_error:\n                    result['wait_recovery_error']=type(observation_error).__name__+': '+str(observation_error)")
    trial=once(trial,'        e=runtime.evidence()',
        "        if result.get('wait_recovery_error'):raise RuntimeError('Wait recovery failed: '+result['wait_recovery_error'])\n        result['video_wait_summary']=validate(wait_report,wait_contract)\n        result['ps_prefetch_enabled']=False\n        del wait_report\n        e=runtime.evidence()")
    trial=trial.replace('M369','M375').replace('all8_requests_completed','bounded_request_completed').replace('performance_measurements_collected','wait_measurements_collected')
    trial=once(trial,"result['measurement_scope']='Preloaded original request, original timers, warm original PS code cache; initialization and all SHA validation outside request'",
        "result['measurement_scope']='One original fixed159 candidate request with narrow Future wait observation; diagnostic overhead included, no new performance comparison'")
    atomic(PKG/'m375_trials.py',trial.encode('utf-8'))
    gate=(OLD/'m369_light_video_gate.py').read_text(encoding='utf-8').replace('M369','M375').replace('m369_trials','m375_trials').replace('m369_export_result','m375_export_result')
    gate=once(gate,'is_candidate=False  # Stable is always the first member of ABBABAAB','is_candidate=True  # One verified candidate, narrow wait observation only')
    gate=gate.replace('/home/ubuntu/m369_light_video_01','/home/ubuntu/m375_video_wait_01')
    gate=gate.replace('balanced-fixed159-video-light-performance','fixed159-video-narrow-future-wait').replace('PASS_M375_LIGHT_VIDEO_MEASUREMENTS','PASS_M375_FIXED_VIDEO_WAIT')
    gate=gate.replace('Adjudicate all8 original full-request times and order variability; no automatic promotion','Interpret cumulative parse wait, gate_up share, reuse versus tail; no automatic scheduling change or promotion')
    gate=once(gate,"        result['prior_board_sha256'] = PRIOR_SHA",
        "        result['prior_board_sha256'] = PRIOR_SHA\n        wait_path=HERE/'WAIT_PREREQUISITE.json'\n        if sha256(wait_path)!='031cf6e2e506f5296998e6e8dfbeba0e87480f41fc07f023aaf3fc6fc79147a2' or json.loads(wait_path.read_text(encoding='utf-8'))['status']!='PASS_SINGLE_LAYER_ACTUAL_WAIT_OBSERVED':raise RuntimeError('Synchronized layer wait prerequisite differs')\n        result['wait_prerequisite_sha256']=sha256(wait_path)")
    atomic(PKG/'m375_video_wait_gate.py',gate.encode('utf-8'))
    export=(OLD/'m369_export_result.py').read_text(encoding='utf-8').replace('M369','M375').replace('/home/ubuntu/m369_light_video_01','/home/ubuntu/m375_video_wait_01').replace('balanced-fixed159-video-light-performance','fixed159-video-narrow-future-wait')
    atomic(PKG/'m375_export_result.py',export.encode('utf-8'))
    runner=(OLD/'run_m369_light_video.sh').read_text(encoding='utf-8').replace('M369','M375').replace('m369_export_result','m375_export_result').replace('m369_light_video_gate','m375_video_wait_gate').replace('/home/ubuntu/m369_light_video_01','/home/ubuntu/m375_video_wait_01').replace('M375_ENABLE_LIGHT_VIDEO','M375_ENABLE_VIDEO_WAIT')
    runner=once(runner,'task_python=/usr/local/share/pynq-venv/bin/python','task_python=/usr/local/share/pynq-venv/bin/python\nexport PYTHONDONTWRITEBYTECODE=1')
    atomic(PKG/'run_m375_video_wait.sh',runner.encode('utf-8'))
    assembly=(BASE/'candidates/M371-candidate-prefill-profile-01/m371_assemble.py').read_text(encoding='utf-8').replace('M371','M375')
    atomic(PKG/'m375_assemble.py',assembly.encode('utf-8'))
    trees={p.stem:ast.parse(p.read_text(encoding='utf-8'),feature_version=(3,10)) for p in PKG.glob('*.py')}
    closure=json.loads((PKG/'SOURCE_CLOSURE.json').read_text(encoding='utf-8'))
    allowed=set(sys.stdlib_module_names)|set(closure['modules'])|{'numpy','pynq','tokenizers'}
    missing=[]
    for module,tree in trees.items():
        for node in ast.walk(tree):
            names=[r.name.split('.')[0] for r in node.names] if isinstance(node,ast.Import) else ([(node.module or '').split('.')[0]] if isinstance(node,ast.ImportFrom) else [])
            missing.extend((module,n) for n in names if n and n not in trees and n not in allowed)
    assert not missing,missing
    table=next(t for t in symtable.symtable(gate,'gate','exec').get_children() if t.get_name()=='main')
    assert next(t for t in table.get_children() if t.get_name()=='tracked_allocate').lookup('SHAPES').is_global()
    release=ROOT/'release_staging/kv260-mage-vl-4b-prebuilt-install-20260926-v7'
    for row in closure['files']:assert sha(release/row['path'])==row['sha256']
    hardware=json.loads((PKG/'HARDWARE_CLOSURE.json').read_text(encoding='utf-8'))
    assert hardware['status']=='PASS_ALL_NEW_CIRCUIT_PREREQUISITES'
    for row in hardware['prerequisites']:assert sha(ROOT/row['path'])==row['sha256']
    for name in ('m369_light_policy.py','owned_buffer_release.py','VIDEO_EXPECTED.json','VISUAL_EXPECTED.json','SOURCE_CLOSURE.json','HARDWARE_CLOSURE.json'):
        assert sha(PKG/name)==sha(OLD/name)
    rows=[dict(path=p.name,bytes=p.stat().st_size,sha256=sha(p)) for p in sorted(PKG.iterdir())]
    atomic(PKG/'SHA256SUMS',''.join(r['sha256']+'  '+r['path']+'\n' for r in rows).encode('ascii'))
    rows.append(dict(path='SHA256SUMS',bytes=(PKG/'SHA256SUMS').stat().st_size,sha256=sha(PKG/'SHA256SUMS')))
    atomic(PKG/'PACKAGE_MANIFEST.json',encoded(dict(schema='m375-fixed-video-narrow-wait-v1',files=rows,file_count=len(rows),total_bytes=sum(r['bytes'] for r in rows))))
    assert {p.name for p in PKG.iterdir()}=={r['path'] for r in rows}|{'PACKAGE_MANIFEST.json'}
    result=dict(status='PASS_OFFLINE_FIXED_VIDEO_WAIT_PACKAGE_PREPARATION',build_id='0x4D333537',prior_sha256=prerequisites,
        manifest_sha256=sha(PKG/'PACKAGE_MANIFEST.json'),file_count=len(rows),total_bytes=sum(r['bytes'] for r in rows),
        original_math_input_reference_policy_unchanged=True,python310_syntax=True,recursive_missing=missing,
        hardware_prerequisites_same_sha=True,extra_cma_allocations=0,new_workers=0,ps_prefetch_enabled=False,
        board_run=False,actual_video_wait_s=None,performance_pass=False,
        next_step='New package callback and collector/control failure tests; preparation only, no upload or board request yet.')
    atomic(OUT/'RESULT.json',encoded(result),immutable=True);digest=sha(OUT/'RESULT.json')
    sync('latest_m375_video_wait_preparation',dict(status=result['status'],result=(OUT/'RESULT.json').relative_to(ROOT).as_posix(),sha256=digest,manifest_sha256=result['manifest_sha256'],board_run=False),
        f'## M375 原固定159视频窄等待观察包准备（2026-10-03）\n\nBuild0x4D333537；只一次原请求，0新增DMA/worker/PS预取；复用M369同SHA输入/视觉/logits/72KV参考、原稀疏容量/分配/释放与47硬件证据。仅语言154family、770pack/770parse；复用M373/M374原等待钩子，压缩trace和独立校验。递归missing=0、Python3.10及SHAPES作用域通过。准备SHA {digest}，manifest {result["manifest_sha256"]}。未上传/上板，下一步新回调/收集负例及控制检查；不重复单层/大画像/八次性能。')
    print(json.dumps(dict(status=result['status'],sha256=digest,manifest_sha256=result['manifest_sha256'],files=len(rows),bytes=result['total_bytes'])))

if __name__=='__main__':main()
