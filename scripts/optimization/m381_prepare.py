"""New parser variant balanced request comparison, both on the parallel kernel."""
import ast,json,shutil,sys,symtable
from m351_workflow import ROOT,HERE,BASE,sha,atomic,encoded,sync
from m377_prepare import once
OLD=BASE/'candidates/M369-light-video-01'
PKG=BASE/'candidates/M381-gate-up-performance-01'
def main():
    if PKG.exists():raise RuntimeError('Immutable package exists')
    board=json.loads((ROOT/'deployment/mage_vl4b/BOARD_GATE_RESULT.json').read_text(encoding='utf-8'));prior=board['latest_m380_gate_up_video_board']
    assert prior['status']=='PASS_M380_FIXED_VIDEO_DIAGNOSTIC' and sha(ROOT/prior['result'])==prior['sha256']
    assert all(prior['sha256'] in (ROOT/n).read_text(encoding='utf-8-sig') for n in ('CURRENT_STATE.md','docsMILESTONES.md'))
    manifest=json.loads((OLD/'PACKAGE_MANIFEST.json').read_text(encoding='utf-8'))
    for r in manifest['files']:assert sha(OLD/r['path'])==r['sha256']
    PKG.mkdir(parents=True)
    skip={'m369_assemble.py','m369_light_video_gate.py','m369_trials.py','m369_export_result.py','run_m369_light_video.sh','SHA256SUMS'}
    for r in manifest['files']:
        if r['path'] not in skip:shutil.copyfile(OLD/r['path'],PKG/r['path'])
    for n in ('m376_gate_up_workers.py','m370_patch_scope.py'):shutil.copyfile(HERE/n,PKG/n)
    assembly=(BASE/'candidates/M380-gate-up-video-01/m380_assemble.py').read_text(encoding='utf-8').replace('M380','M381').replace('/home/ubuntu/m368_staged_video_candidate_03','/home/ubuntu/m369_light_video_candidate_01').replace(sha(BASE/'candidates/M368-staged-video-03/PACKAGE_MANIFEST.json'),sha(OLD/'PACKAGE_MANIFEST.json'))
    atomic(PKG/'m381_assemble.py',assembly.encode('utf-8'))
    gate=(OLD/'m369_light_video_gate.py').read_text(encoding='utf-8').replace('M369','M381').replace('m369_trials','m381_trials').replace('m369_export_result','m381_export_result').replace('/home/ubuntu/m369_light_video_01','/home/ubuntu/m381_gate_up_performance_01')
    gate=once(gate,'is_candidate=False  # Stable is always the first member of ABBABAAB','is_candidate=True  # Both parser variants use identical current parallel hardware')
    gate=once(gate,"        result['prior_board_sha256'] = PRIOR_SHA","        result['prior_board_sha256'] = PRIOR_SHA\n        video_path=Path('/home/ubuntu/m380_gate_up_video_01/B1/load-memory.json')\n        video=json.loads(video_path.read_text(encoding='utf-8'))\n        if sha256(video_path)!='"+prior['sha256']+"' or video['status']!='PASS_M380_FIXED_VIDEO_DIAGNOSTIC' or video['gate_return_code']!=0 or not video['safe_buffers_released']:raise RuntimeError('Actual new parser video prerequisite differs')\n        result['two_parser_video_sha256']=sha256(video_path)")
    gate=once(gate,'from measurement import sha256, write_json','from measurement import sha256, write_json\nfrom m370_patch_scope import PatchScope')
    gate=once(gate,'    allocations = []; restorations = []; slots = []','    allocations = []; slots = []; registry = PatchScope()')
    gate=once(gate,'        original = getattr(obj,name); restorations.append((obj,name,original)); setattr(obj,name,replacement)\n        return original','        return registry.patch(obj,name,replacement)')
    gate=once(gate,"        result['build_id']='0x4D395832/0x4D333537'","        result['build_id']='0x4D333537'")
    gate=once(gate,"            TARGET=CANDIDATE if variant=='B' else STABLE","            TARGET=CANDIDATE")
    gate=once(gate,"            TARGET_SHA=CAND_SHA if variant=='B' else STABLE_SHA","            TARGET_SHA=CAND_SHA")
    gate=once(gate,"            TARGET_BUILD='0x4D333537' if variant=='B' else '0x4D395832'","            TARGET_BUILD='0x4D333537'")
    gate=once(gate,"            verify_frozen_package(TARGET,TARGET_SHA,legacy_manifest=variant=='A')","            verify_frozen_package(TARGET,TARGET_SHA,legacy_manifest=False)")
    gate=once(gate,'        run_trials(engine,runtime,policy,base,CANDIDATE,HERE,result,new_board,patch)',"        def restore_trial(owner,owned_policy):\n            if not owner._m368_closed or not owned_policy.safe():raise RuntimeError('Trial lifecycle not proven; retain owner')\n            count=registry.restore_owner(owner,completion_proven=True,release_proven=True)\n            if any(e[0] is owner for e in registry.entries):raise RuntimeError('Trial owner retained by registry')\n            return count\n        run_trials(engine,runtime,policy,base,CANDIDATE,HERE,result,new_board,patch,restore_trial)")
    gate=once(gate,'            for obj,name,original in reversed(restorations): setattr(obj,name,original)','            registry.restore_all(completion_proven=True,release_proven=True)')
    gate=gate.replace('balanced-fixed159-video-light-performance','balanced-fixed159-video-one-versus-two-parser-performance')
    atomic(PKG/'m381_light_video_gate.py',gate.encode('utf-8'))
    trials=(OLD/'m369_trials.py').read_text(encoding='utf-8').replace('M369','M381')
    trials=once(trials,'import numpy as np','import numpy as np\nfrom contextlib import nullcontext\nfrom m376_gate_up_workers import GateUpWorkers')
    trials=once(trials,'def run_trials(engine,runtime,policy,base,candidate,here,result,new_board,patch):','def run_trials(engine,runtime,policy,base,candidate,here,result,new_board,patch,restore_trial):')
    trials=once(trials,"        build=0x4d395832 if variant=='A' else 0x4d333537","        build=0x4d333537")
    trials=once(trials,'        captured.clear();stage_ms.clear()',"        parser_scope=GateUpWorkers(runtime,workers=2,enabled=True) if variant=='B' else None\n        # Source pinning/AST preparation is outside the original request timers.\n        captured.clear();stage_ms.clear()")
    trials=once(trials,'        for event,payload in engine.stream(request):events.append((event,payload))',"        with parser_scope if parser_scope is not None else nullcontext():\n            for event,payload in engine.stream(request):events.append((event,payload))\n        parser_report=parser_scope.report() if parser_scope is not None else dict(parse_workers=1,original_single_worker_dispatch=True,bindings_restored=True,extra_dma_allocations=0)\n        if parser_scope is not None and parser_report['gate_up_calls']!=36:raise RuntimeError('Candidate gate_up coverage differs')\n        if any(t.name.startswith(('m238-parse','m238-pack')) for t in threading.enumerate()):raise RuntimeError('Worker retained after request')")
    trials=once(trials,"        sample['released_buffers']=list(result['released_buffers']);sample['safe_buffers_released']=True","        sample['released_buffers']=list(result['released_buffers']);sample['safe_buffers_released']=True\n        sample['parser_scope']=parser_report\n        sample['restored_owner_patch_count']=restore_trial(runtime,policy)\n        sample['owner_registry_cleared']=True")
    trials=once(trials,'        del logits,kv,events,e,row,transactions','        del logits,kv,events,e,row,transactions,head,observed_head,timed_head,parser_scope')
    trials=once(trials,"    result['performance_measurements_collected']=True","    result['performance_measurements_collected']=True\n    result['ps_prefetch_enabled']=False\n    result['comparison']='Current parallel hardware: original one parser versus gate_up two parsers'\n    result['historical_hardware_40_81_percent_result_unchanged']=True")
    atomic(PKG/'m381_trials.py',trials.encode('utf-8'))
    export=(OLD/'m369_export_result.py').read_text(encoding='utf-8').replace('M369','M381').replace('/home/ubuntu/m369_light_video_01','/home/ubuntu/m381_gate_up_performance_01').replace('balanced-fixed159-video-light-performance','balanced-fixed159-video-one-versus-two-parser-performance')
    atomic(PKG/'m381_export_result.py',export.encode('utf-8'))
    runner=(OLD/'run_m369_light_video.sh').read_text(encoding='utf-8').replace('M369','M381').replace('m369_export_result','m381_export_result').replace('m369_light_video_gate','m381_light_video_gate').replace('/home/ubuntu/m369_light_video_01','/home/ubuntu/m381_gate_up_performance_01')
    if 'export PYTHONDONTWRITEBYTECODE=1' not in runner:runner=once(runner,'task_python=/usr/local/share/pynq-venv/bin/python','task_python=/usr/local/share/pynq-venv/bin/python\nexport PYTHONDONTWRITEBYTECODE=1')
    atomic(PKG/'run_m381_light_video.sh',runner.encode('utf-8'))
    closure=json.loads((PKG/'SOURCE_CLOSURE.json').read_text(encoding='utf-8'));trees={p.stem:ast.parse(p.read_text(encoding='utf-8'),feature_version=(3,10)) for p in PKG.glob('*.py')};allowed=set(sys.stdlib_module_names)|set(closure['modules'])|{'numpy','pynq','tokenizers'};missing=[]
    for mod,tree in trees.items():
        for node in ast.walk(tree):
            names=[r.name.split('.')[0] for r in node.names] if isinstance(node,ast.Import) else ([(node.module or '').split('.')[0]] if isinstance(node,ast.ImportFrom) else [])
            missing.extend((mod,n) for n in names if n and n not in trees and n not in allowed)
    assert not missing,missing
    table=next(t for t in symtable.symtable(gate,'gate','exec').get_children() if t.get_name()=='main');assert next(t for t in table.get_children() if t.get_name()=='tracked_allocate').lookup('SHAPES').is_global()
    assert gate.index('engine.load()')<gate.index("patch(video_server,'BUILD_ID',TARGET_BUILD)")
    for n in ('m369_light_policy.py','m368_stage_policy.py','VIDEO_EXPECTED.json','VISUAL_EXPECTED.json','SOURCE_CLOSURE.json','HARDWARE_CLOSURE.json','owned_buffer_release.py'):assert sha(PKG/n)==sha(OLD/n)
    rows=[dict(path=p.name,bytes=p.stat().st_size,sha256=sha(p)) for p in sorted(PKG.iterdir())];atomic(PKG/'SHA256SUMS',''.join(r['sha256']+'  '+r['path']+'\n' for r in rows).encode('ascii'));rows.append(dict(path='SHA256SUMS',bytes=(PKG/'SHA256SUMS').stat().st_size,sha256=sha(PKG/'SHA256SUMS')))
    atomic(PKG/'PACKAGE_MANIFEST.json',encoded(dict(schema='m381-parser-width-balanced-request-v1',files=rows,file_count=len(rows),total_bytes=sum(r['bytes'] for r in rows))))
    r=dict(status='PASS_OFFLINE_TWO_PARSER_PERFORMANCE_PREPARATION',manifest_sha256=sha(PKG/'PACKAGE_MANIFEST.json'),two_parser_video_sha256=prior['sha256'],base_manifest_sha256=sha(OLD/'PACKAGE_MANIFEST.json'),recursive_import_missing=missing,python310_syntax=True,same_hardware_both_variants=True,order='ABBABAAB',original_timers_and_post_timer_hashes=True,scope_AST_preparation_outside_timer=True,scoped_trial_owner_cleanup=True,original_video_memory_policy_same_sha=True,extra_cma_bytes=0,board_run=False,performance_pass=False)
    path=BASE/'runs/M381-gate-up-performance-preparation-01/RESULT.json';atomic(path,encoded(r),immutable=True);digest=sha(path);sync('latest_m381_gate_up_performance_preparation',dict(status=r['status'],result=path.relative_to(ROOT).as_posix(),sha256=digest,manifest_sha256=r['manifest_sha256']),f'## M381 同并行核单/双解析worker完整请求对照准备（2026-10-03）\n\n新视频数值SHA {prior["sha256"]}已同步才准备；A原1/B只gate_up2，全部Build0x4D333537，ABBABAAB。原请求timers/100ms监控、计时后完整数值/SHA和同SHA内存policy保持；M370 owner级安全restore删除继承覆盖、清注册表，及时丢弃历史张量/绑定。0额外CMA/PS预读。递归missing=0/3.10/加载身份顺序通过。准备 SHA {digest}；还需实际控制编排及回收支持，未新增性能。')
    print('M381_PREPARED',digest,len(rows))
if __name__=='__main__':main()
