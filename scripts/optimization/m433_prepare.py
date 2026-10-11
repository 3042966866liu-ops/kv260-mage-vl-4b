"""Prepare one bounded complete-request warm experiment, no board execution."""
import ast
import json
from m351_workflow import ROOT, BASE, HERE, atomic, encoded, sha, sync
from m427_prepare import once

OLD = BASE / 'candidates/M432-late11-integrated-video-02'
PKG = BASE / 'candidates/M433-late11-complete-request-warm-01'


def main():
    if PKG.exists():
        raise RuntimeError('Immutable packet exists')
    board = json.loads((ROOT / 'deployment/mage_vl4b/BOARD_GATE_RESULT.json').read_bytes())
    prior = {}
    for key in ('latest_m432_integrated_board', 'latest_m432_integrated_closure',
                'latest_m433_complete_request_protocol', 'latest_m433_timed_provider_component'):
        e = board[key]
        if sha(ROOT / e['result']) != e['sha256'] or not all(e['sha256'] in (ROOT / n).read_text(encoding='utf-8-sig') for n in ('CURRENT_STATE.md', 'docsMILESTONES.md')):
            raise RuntimeError('Unsynchronized prerequisite')
        prior[key] = e
    if prior['latest_m432_integrated_closure']['numerical_pass'] is not True or prior['latest_m433_timed_provider_component']['status'] != 'PASS_M433_ACTUAL_TIMED_PROVIDER_FIXTURE_ONLY':
        raise RuntimeError('Numerical and actual timed-provider gates required')
    component = json.loads((ROOT / prior['latest_m433_timed_provider_component']['result']).read_bytes())
    if component['source_sha256'] != sha(HERE / 'm433_timed_visual.py'):
        raise RuntimeError('Actual timed provider source changed')
    protocol = (ROOT / prior['latest_m433_complete_request_protocol']['result']).with_name('PROTOCOL.json')
    if sha(protocol) != prior['latest_m433_complete_request_protocol']['protocol_sha256']:
        raise RuntimeError('Frozen protocol changed')
    manifest = json.loads((OLD / 'PACKAGE_MANIFEST.json').read_bytes())
    for row in manifest['files']:
        if sha(OLD / row['path']) != row['sha256'] or (OLD / row['path']).stat().st_size != row['bytes']:
            raise RuntimeError('Passed numerical packet changed')
    gate = (OLD / 'm432_gate.py').read_text(encoding='utf-8')
    gate = gate.replace('m432_late11_integrated_video_01', 'm433_late11_warm_request_01')
    gate = gate.replace('integrated-fixed159-visual-language-quality', 'controlled-warm-complete-request-performance')
    gate = gate.replace('M432', 'M433').replace('from m432_trials import run', 'from m433_trials import run')
    gate = once(gate, 'from m369_light_policy import StagePolicy', 'from m433_light_policy import StagePolicy')
    gate = gate.replace('> 900', '> 3000')
    gate = once(gate, 'from m432_request_visual import VisualProvider\n        provider=VisualProvider(engine,runtime,policy,base,HERE,result,integrated_sources)',
                'from m433_timed_visual import TimedVisualProvider\n        provider=TimedVisualProvider(engine,runtime,policy,base,HERE,result,integrated_sources,enabled=True)')
    gate = gate.replace('PASS_M433_INTEGRATED_VIDEO_NUMERICAL', 'PASS_M433_CONTROLLED_WARM_MEASUREMENTS_COLLECTED')
    gate = once(gate, "        result['integrated_sources_checked_before_overlay']=True", """        from m433_prerequisite import verify as verify_complete_numerical
        perf_plan=json.loads((HERE/'PERFORMANCE_PLAN.json').read_bytes())
        saved=verify_complete_numerical(perf_plan)
        if sha256(HERE/'WARM_PROTOCOL.json')!=perf_plan['protocol_sha256']:raise RuntimeError('Frozen whole-request protocol differs')
        result['complete_request_numerical_source_sha256']=perf_plan['integrated_numerical_sha256']
        result['temperature_measurement_enabled']=False
        result['integrated_sources_checked_before_overlay']=True""")
    gate = once(gate, "(1 if policy is not None and policy.ever else 0)+len(result.get('transactions',[]))+len(result.get('visual_transactions',[]))",
                "(1 if policy is not None and policy.ever else 0)+result.get('completed_language_physical',0)+result.get('completed_visual_physical',0)+len(result.get('transactions',[]))+len(result.get('visual_transactions',[]))")
    gate = gate.replace('from m432_export import emit_saved', 'from m433_export import emit_saved')
    gate = once(gate, "result['next_step'] = 'Close saved-feature decision consistency; no automatic expansion or performance'", "result['next_step'] = 'Close exactly the saved fixed warm experiment; no extra requests, fitted threshold or production promotion'")
    trials = (HERE / 'm425_trials.py').read_text(encoding='utf-8').replace('M425', 'M433')
    trials = trials.replace('from m423_trials import delta', 'from m432_trials import delta').replace('from m423_saved_features import tensor', 'from m428_saved_features import tensor')
    trials = trials.replace('(52 if index else 0)', '(286 if index else 0)').replace("len(result['visual_staging'])!=4", "len(result['visual_staging'])!=22").replace('!=8912896', '!=49020928')
    trials = trials.replace('all_four_bindings_restored=True', 'all_visual_bindings_restored=True')
    trials = once(trials, "        if len(transactions)!=781", "        expected_transactions=provider.sources['language']['transactions'][index*781:(index+1)*781]\n        if transactions!=expected_transactions:raise RuntimeError('Complete post-timer language physical sequence differs')\n        if len(transactions)!=781")
    texts = {'m433_gate.py': gate, 'm433_trials.py': trials,
             'm433_timed_visual.py': (HERE / 'm433_timed_visual.py').read_text(encoding='utf-8'),
             'm430_timed_scope.py': (HERE / 'm430_timed_scope.py').read_text(encoding='utf-8')}
    texts['m433_light_policy.py'] = (HERE / 'm433_light_policy.py').read_text(encoding='utf-8')
    texts['m433_prerequisite.py'] = (HERE / 'm433_prerequisite.py').read_text(encoding='utf-8')
    for n in ('m425_warm.py', 'm425_environment.py'):
        texts[n] = (HERE / n).read_text(encoding='utf-8')
    texts['m433_export.py'] = (OLD / 'm432_export.py').read_text(encoding='utf-8').replace('M432', 'M433').replace('m432_late11_integrated_video_01', 'm433_late11_warm_request_01').replace('integrated-fixed159-visual-language-quality', 'controlled-warm-complete-request-performance')
    texts['m433_entry.py'] = (OLD / 'm432_entry.py').read_text(encoding='utf-8').replace('m432_gate.py', 'm433_gate.py')
    texts['run_m433.sh'] = (OLD / 'run_m432.sh').read_text(encoding='utf-8').replace('m432', 'm433').replace('M432', 'M433').replace('m433_late11_integrated_video_01', 'm433_late11_warm_request_01')
    texts['m433_assemble.py'] = (OLD / 'm432_assemble.py').read_text(encoding='utf-8').replace('/home/ubuntu/m428_saved_feature_candidate_01', '/home/ubuntu/m432_late11_integrated_candidate_02').replace(sha(BASE / 'candidates/M428-late11-saved-language-02/PACKAGE_MANIFEST.json'), sha(OLD / 'PACKAGE_MANIFEST.json')).replace('M432_ASSEMBLY_PASS', 'M433_ASSEMBLY_PASS')
    plan = json.loads((OLD / 'PLAN.json').read_bytes())
    plan.update(performance_measurement=True, maximum_requests=12, integrated_visual_calls=12, integrated_language_calls=12,
                prerequisites=prior, request_boundary='Four ABBA warmups and eight ABBABAAB formal original stream requests; no additional samples')
    texts['PLAN.json'] = encoded(plan).decode('utf-8')
    texts['WARM_PROTOCOL.json'] = protocol.read_text(encoding='utf-8')
    e = prior['latest_m432_integrated_board']
    texts['PERFORMANCE_PLAN.json'] = encoded(dict(protocol_sha256=sha(protocol),
        integrated_numerical_result='/home/ubuntu/m432_late11_integrated_video_01/BOARD_RESULT.json',
        integrated_numerical_sha256=e['sha256'], integrated_numerical_bytes=(ROOT / e['result']).stat().st_size)).decode('utf-8')
    if not gate.index('perf_plan=') < gate.index('import pynq'):
        raise RuntimeError('Performance prerequisites must precede resources')
    PKG.mkdir(parents=True)
    excluded = {'m432_gate.py', 'm432_entry.py', 'm432_export.py', 'm432_assemble.py', 'run_m432.sh', 'PLAN.json', 'SHA256SUMS', 'DEPENDENCY_CLOSURE.json'}
    for row in manifest['files']:
        if row['path'] not in excluded:
            atomic(PKG / row['path'], (OLD / row['path']).read_bytes(), immutable=True)
    for n, text in texts.items():
        if n.endswith('.py'):
            ast.parse(text, feature_version=(3, 10))
        atomic(PKG / n, text.encode('utf-8'), immutable=True)
    folders = [PKG]
    for row in plan['visual_reused_packages']:
        matches = [p.parent for p in (BASE / 'candidates').glob('*/PACKAGE_MANIFEST.json') if sha(p) == row['manifest_sha256']]
        if len(matches) != 1:
            raise RuntimeError('Unique same-SHA reused package required')
        folders.extend(matches)
    folders.append(BASE / 'candidates/M368-staged-video-03')
    modules = {}
    for folder in folders:
        for p in folder.glob('*.py'):
            modules.setdefault(p.stem, p)
    for row in json.loads((PKG / 'M348_SOURCE_IDENTITIES.json').read_bytes())['files']:
        for p in (ROOT / row['path'], ROOT / 'release_staging/kv260-mage-vl-4b-prebuilt-install-20260926-v7' / row['path']):
            if p.is_file() and p.stat().st_size == row['bytes'] and sha(p) == row['sha256']:
                modules.setdefault(p.stem, p)
                break
    seen, missing = set(), []
    def visit(name):
        if name in seen:
            return
        seen.add(name)
        tree = ast.parse(modules[name].read_text(encoding='utf-8-sig'), feature_version=(3, 10))
        deps = [a.name.split('.')[0] for n in ast.walk(tree) if isinstance(n, ast.Import) for a in n.names]
        deps += [(n.module or '').split('.')[0] for n in ast.walk(tree) if isinstance(n, ast.ImportFrom)]
        for dep in deps:
            if dep in modules:
                visit(dep)
            elif len(dep) > 1 and dep[0] == 'm' and dep[1].isdigit():
                missing.append([name, dep])
    for name in ('m433_gate', 'm433_entry', 'm433_export', 'm433_assemble'):
        visit(name)
    if missing:
        raise RuntimeError('Recursive dependency closure missing: ' + repr(missing))
    atomic(PKG / 'DEPENDENCY_CLOSURE.json', encoded(dict(missing=missing, recursive_modules=len(seen), files={n: sha(modules[n]) for n in sorted(seen)})), immutable=True)
    atomic(PKG / 'SHA256SUMS', ''.join(f'{sha(p)}  {p.name}\n' for p in sorted(PKG.iterdir())).encode('ascii'), immutable=True)
    files = sorted(PKG.iterdir())
    manifest = dict(file_count=len(files), total_bytes=sum(p.stat().st_size for p in files), files=[dict(path=p.name, bytes=p.stat().st_size, sha256=sha(p)) for p in files])
    atomic(PKG / 'PACKAGE_MANIFEST.json', encoded(manifest), immutable=True)
    record = dict(status='PREPARED_M433_COMPLETE_REQUEST_WARM_SUPPORT_PENDING', prerequisites=prior,
        manifest_sha256=sha(PKG / 'PACKAGE_MANIFEST.json'), file_count=manifest['file_count'], total_bytes=manifest['total_bytes'],
        completed_language_physical_expected=9372, completed_visual_physical_expected=1716, total_physical_expected=11089,
        recursive_modules=len(seen), missing=missing,
        complete_stream_timing=True, numerical_hashes_after_timer=True, extra_DMA=0, fixed_CMA_floor=None,
        board_run=False, performance_pass=False, temperature_measurement_enabled=False)
    out = BASE / 'runs/M433-complete-request-preparation-01/RESULT.json'
    atomic(out, encoded(record), immutable=True)
    sync('latest_m433_complete_request_preparation', dict(status=record['status'], result=out.relative_to(ROOT).as_posix(), sha256=sha(out), manifest_sha256=record['manifest_sha256']),
         f'## M433 后11层完整请求轻量包准备（2026-10-07）\n\nSHA {sha(out)}，manifest {record["manifest_sha256"]}，固定4预热＋8正式。原stream complete计时、22暂存/286视觉事务均计入，完整特征/logits/72KV及语言物理序列计时后核对，9372语言＋1716视觉＋1minimal预期11089物理。原七DMA/0新增、不测温；实际轻量provider组件已过，仍需原stream组件、递归依赖及实际export/collector/control/assembly支持；未上传或性能。')
    print('M433_PREPARATION_SYNC', sha(out), record['manifest_sha256'])


if __name__ == '__main__':
    main()
